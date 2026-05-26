import rclpy
import time
import json
import cv2
import os
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
from scipy.spatial.transform import Rotation

# ==============================
# 환경 설정
# ==============================
ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"

MODEL_PATH = "/home/rokey/Downloads/CodeLLM/resource/towel_yolo26n_seg_v5_best.pt"
NPY_PATH = "/home/rokey/Downloads/CodeLLM/resource/T_gripper2camera.npy"

SCAN_SECONDS = 10.0
YOLO_CONF = 0.4

MIN_DETECTIONS = 50
DIST_THRESHOLD = 30.0

# 💡 Z축 오프셋 높이 설정 (mm 단위)
Z_OFFSET = 350.0
ORIGIN_OFFSET = -20.0
SAVE_JSON = True
OUTPUT_JSON_PATH = "/home/rokey/Downloads/CodeLLM/point/scan_result_base_coord.json"

class RealsenseDirect:
    def __init__(self):
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        self.profile = self.pipeline.start(self.config)
        self.align = rs.align(rs.stream.color)
        intr = self.profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
        self.intrinsics = {"fx": intr.fx, "fy": intr.fy, "ppx": intr.ppx, "ppy": intr.ppy}
        self.color_frame = None
        self.depth_frame = None
        print("✅ RealSense 연결 성공")

    def update_frames(self):
        try:
            frames = self.pipeline.wait_for_frames(1000)
            aligned_frames = self.align.process(frames)
            color_f = aligned_frames.get_color_frame()
            depth_f = aligned_frames.get_depth_frame()
            if not color_f or not depth_f: return False
            self.color_frame = np.asanyarray(color_f.get_data())
            self.depth_frame = np.asanyarray(depth_f.get_data())
            return True
        except Exception as e:
            print(f"⚠️ RealSense 프레임 갱신 실패: {e}")
            return False

    def get_color_frame(self): return self.color_frame
    def get_depth_frame(self): return self.depth_frame
    def get_camera_intrinsic(self): return self.intrinsics
    def shutdown(self): self.pipeline.stop()

class YoloModel:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def get_all_best_detections(self, cam_node):
        color_frame = cam_node.get_color_frame()
        if color_frame is None: return [], None
        results = self.model(color_frame, conf=YOLO_CONF, verbose=False)
        annotated_frame = results[0].plot() if len(results) > 0 else color_frame
        valid_detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                detected_name = self.model.names[cls_id]
                valid_detections.append((detected_name, xyxy, conf))
        return valid_detections, annotated_frame

class ObjectDetector:
    def __init__(self, cam_node):
        self.cam_node = cam_node
        self.intrinsics = self.cam_node.get_camera_intrinsic()

    def compute_positions(self, valid_detections):
        state_list = []
        depth_frame = self.cam_node.get_depth_frame()
        if depth_frame is None: return state_list
        for target, box, conf in valid_detections:
            cx, cy = int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)
            try:
                cz = depth_frame[cy, cx]
                if cz == 0: continue
            except IndexError: continue
            x_3d = (cx - self.intrinsics["ppx"]) * cz / self.intrinsics["fx"]
            y_3d = (cy - self.intrinsics["ppy"]) * cz / self.intrinsics["fy"]
            state_list.append([target, [float(x_3d), float(y_3d), float(cz)]])
        return state_list

class IntegratedScanner:
    def __init__(self, node):
        self.node = node
        self.logger = node.get_logger()
        self.vision_buffer = []
        try:
            self.gripper2cam = np.load(NPY_PATH)
            self.logger.info("✅ gripper2camera 캘리브레이션 파일 로드 성공")
        except Exception as e:
            self.gripper2cam = np.eye(4)
            self.logger.warn(f"⚠️ 캘리브레이션 파일 로드 실패. 단위 행렬 사용: {e}")

    def get_robot_pose_matrix(self, posx):
        x, y, z, rx, ry, rz = posx
        R = Rotation.from_euler("ZYZ", [rx, ry, rz], degrees=True).as_matrix()
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = [x, y, z]
        return T

    def transform_to_base(self, cam_coords, current_posx):
        base2gripper = self.get_robot_pose_matrix(current_posx)
        base2cam = base2gripper @ self.gripper2cam
        coord = np.append(np.array(cam_coords, dtype=float), 1.0)
        base_coord = base2cam @ coord
        return base_coord[:3]

    def cluster_positions(self, current_posx):
        class_groups = {}
        for target, cam_coords in self.vision_buffer:
            if target == "white":
                target = "white_towel"
            if target == "colored":
                target = "colored_towel"

            base_xyz = self.transform_to_base(cam_coords, current_posx)
            if target not in class_groups: class_groups[target] = []
            class_groups[target].append(base_xyz)
            
        final_results = {}
        for target, xyz_list in class_groups.items():
            clusters = []
            for xyz in xyz_list:
                xyz_np = np.array(xyz, dtype=float)
                added_to_cluster = False
                for cluster in clusters:
                    centroid = np.mean(cluster, axis=0)
                    dist = np.linalg.norm(xyz_np - centroid)
                    if dist <= DIST_THRESHOLD:
                        cluster.append(xyz_np)
                        added_to_cluster = True
                        break
                if not added_to_cluster: clusters.append([xyz_np])
                
            valid_clusters = [cluster for cluster in clusters if len(cluster) >= MIN_DETECTIONS]
            
            if not valid_clusters:
                continue

            centroids = [np.mean(cluster, axis=0) for cluster in valid_clusters]
            sorted_indices = np.argsort([c[1] for c in centroids])

            for order, idx in enumerate(sorted_indices):
                cluster = valid_clusters[idx]
                final_centroid = centroids[idx]
                
                if len(valid_clusters) > 1:
                    target_id = f"{target}_{order + 1}"
                else:
                    target_id = target
                    
                # 💡 1. 원본 좌표 추가


                if final_centroid[0] < 500:
                    
                    final_results[target_id] = {
                        "x": round(float(final_centroid[0]), 1), 
                        "y": round(float(final_centroid[1]), 1), 
                        "z": round(float(final_centroid[2]) + ORIGIN_OFFSET-10, 1),
                        "rx": round(float(150.0), 1), 
                        "ry": round(float(179.0), 1), 
                        "rz": round(float(150.0), 1),
                        "count": int(len(cluster)),
                    }

                    target_id_offset = f"{target_id}_offset"
                    final_results[target_id_offset] = {
                        "x": round(float(final_centroid[0]), 1), 
                        "y": round(float(final_centroid[1]), 1), 
                        "z": round(float(final_centroid[2]) + Z_OFFSET, 1),
                        "rx": round(float(150.0), 1), 
                        "ry": round(float(179.0), 1), 
                        "rz": round(float(150.0), 1),
                        "count": int(len(cluster)),
                    }

                

                final_results[target_id] = {
                    "x": round(float(final_centroid[0]), 1), 
                    "y": round(float(final_centroid[1]), 1), 
                    "z": round(float(final_centroid[2]) + ORIGIN_OFFSET, 1),
                    "rx": round(float(current_posx[3]), 1), 
                    "ry": round(float(current_posx[4]), 1), 
                    "rz": round(float(current_posx[5]), 1),
                    "count": int(len(cluster)),
                }

                # 💡 2. Z축 오프셋 좌표 추가 (소수점 1자리 반올림)
                target_id_offset = f"{target_id}_offset"
                final_results[target_id_offset] = {
                    "x": round(float(final_centroid[0]), 1), 
                    "y": round(float(final_centroid[1]), 1), 
                    "z": round(float(final_centroid[2]) + Z_OFFSET, 1),
                    "rx": round(float(current_posx[3]), 1), 
                    "ry": round(float(current_posx[4]), 1), 
                    "rz": round(float(current_posx[5]), 1),
                    "count": int(len(cluster)),
                }
                
                self.logger.info(f"🎯 객체 확정: [{target_id}] & [{target_id_offset}] 생성 (y좌표: {final_centroid[1]:.2f})")
                
        return final_results

def initialize_robot():
    from DSR_ROBOT2 import set_robot_mode, set_tool, set_tcp, ROBOT_MODE_MANUAL, ROBOT_MODE_AUTONOMOUS
    set_robot_mode(ROBOT_MODE_MANUAL)
    time.sleep(1.0)
    set_tool("Tool Weight")
    set_tcp("GripperDA_v1")
    set_robot_mode(ROBOT_MODE_AUTONOMOUS)
    time.sleep(2.0)

def save_json_result(payload, node):
    output_dir = os.path.dirname(OUTPUT_JSON_PATH)
    os.makedirs(output_dir, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
    node.get_logger().info(f"💾 JSON 저장 완료: {OUTPUT_JSON_PATH}")

def run_scan_module():
    rclpy.init()
    import DR_init
    DR_init.__dsr__id = ROBOT_ID
    DR_init.__dsr__model = ROBOT_MODEL
    node = rclpy.create_node("integrated_scan_node", namespace=ROBOT_ID)
    DR_init.__dsr__node = node

    scanner = IntegratedScanner(node)
    cam = None
    origin = [0, 0, 90, 0, 90, 0]
    scan_pos_j = [-10.61, -34.07, 70.92, 4.45, 108.37, 83.45]
    
    final_payload = {} 

    try:
        from DSR_ROBOT2 import movej, mwait, get_current_posx, wait
        initialize_robot()
        cam = RealsenseDirect()
        yolo = YoloModel(MODEL_PATH)
        detector = ObjectDetector(cam)

        node.get_logger().info("🚀 원점 자세로 이동합니다.")
        movej(origin, vel=100, acc=100)
        mwait()

        node.get_logger().info("📍 스캔 위치로 이동합니다.")
        movej(scan_pos_j, vel=200, acc=200)
        mwait()

        current_posx = get_current_posx()[0]
        node.get_logger().info(f"📸 {SCAN_SECONDS}초 동안 비전 데이터를 수집합니다.")

        scanner.vision_buffer.clear()
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            remaining = SCAN_SECONDS - elapsed
            if remaining <= 0: break

            if not cam.update_frames():
                time.sleep(0.01)
                continue

            valid_detections, annotated_frame = yolo.get_all_best_detections(cam)
            coords = detector.compute_positions(valid_detections)

            for target, cam_coords in coords:
                scanner.vision_buffer.append((target, cam_coords))

            if annotated_frame is not None:
                cv2.putText(annotated_frame, f"Scanning... {remaining:.1f}s", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                cv2.imshow("Integrated Robot YOLO 3D Scanner", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"): break
            wait(0.01)

        final_results = scanner.cluster_positions(current_posx)
        if final_results:
            final_payload = final_results 
            if SAVE_JSON: save_json_result(final_payload, node)
        else:
            node.get_logger().warn("😭 안정적으로 인식된 객체가 없습니다.")

        node.get_logger().info("🏠 원위치로 복귀합니다.")
        movej(origin, vel=100, acc=100)
        mwait()
        
        return final_payload 

    finally:
        try:
            from DSR_ROBOT2 import movej, wait
            movej(origin, vel=100, acc=100)
            wait(1.0)
        except: pass
        if cam is not None: cam.shutdown()
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()