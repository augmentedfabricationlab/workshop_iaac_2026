import roslibpy
import time
from fabrication_manager.task import Task
from compas_robots import Configuration
from compas.geometry import Translation, Rotation, Frame, Box, Transformation, Point, Quaternion, Vector, distance_point_point
from compas.datastructures import Mesh
from compas_rhino.conversions import plane_to_compas_frame, frame_to_rhino_plane, box_to_rhino
import numpy as np
import math
from assembly_information_model import Part
import open3d
import random
import os
from scipy.spatial.transform import Rotation as R
from mobile_robot_control.pointcloud_processing.icp import preprocess_point_cloud_icp, evaluate_local_registration, execute_icp_local_registration
from ur_fabrication_control.direct_control.fabrication import URTask
from ur_fabrication_control.direct_control import URScript
from ur_fabrication_control.direct_control.common import send_stop
from ur_fabrication_control.direct_control.mixins import URScript, URScript_AreaGrip, URScript_ParallelGrip

__all__ = [
    "ChangeToolFrameTask",
    "PickBrickURTask",
    "PlaceBrickURTask",
    "UpdateAssemblyAttributes",
    "ScanMarkersTask",
    "ScanStackMarkerTask",
    "GlobalMarkerTask",
    "TriggerEstimationTask",
    "CleanBricksTask",
    "ScanBricksTask",
    "ScanSingleBrickAddNewTask",
    "ScanAllBricksTask",
    "ScanSingleBrickTask",
    "ReceiveCameraImageTask"
]
    
def slerp_quat(q1, q2, t):
    q1 = q1 / np.linalg.norm(q1)
    q2 = q2 / np.linalg.norm(q2)
    dot = np.dot(q1, q2)
    if dot < 0.0:
        q2 = -q2
        dot = -dot
    if dot > 0.9995:
        q = q1 + t * (q2 - q1)
        return q / np.linalg.norm(q)
    theta_0 = np.arccos(dot)
    theta = theta_0 * t
    q3 = q2 - q1 * dot
    q3 = q3 / np.linalg.norm(q3)
    return q1 * np.cos(theta) + q3 * np.sin(theta)

def average_frame(frame_a, frame_b):
    # --- Average position ---
    p = Point(
        0.5 * (frame_a.point.x + frame_b.point.x),
        0.5 * (frame_a.point.y + frame_b.point.y),
        0.5 * (frame_a.point.z + frame_b.point.z),
    )

    # --- Average orientation via SLERP ---
    R_a = Rotation.from_frame(frame_a)
    R_b = Rotation.from_frame(frame_b)

    qa = np.array(R_a.quaternion)
    qb = np.array(R_b.quaternion)

    q_avg = slerp_quat(qa, qb, 0.5)
    R_avg = Rotation.from_quaternion(q_avg)

    # --- Build averaged frame ---
    avg_frame = Frame.from_rotation(R_avg)
    avg_frame.point = p
    return avg_frame

# UR tasks.

class ChangeToolFrameTask(Task):
    def __init__(self, robot, tool_name='gripper', key=None):
        super(ChangeToolFrameTask, self).__init__(key)
        self.robot = robot
        self.tool_name = tool_name
        gripper_frame = Frame([0, 0, 0.134], [0, -1, 0], [1, 0, 0])
        camera_frame = Frame.from_quaternion(Quaternion(0, 0, 0.707106, 0.707106), [0.0325, 0.0781, 0.0185])
        if tool_name == 'gripper':
            self.tool_frame = gripper_frame
        else:
            self.tool_frame = camera_frame
        
    def run(self, stop_thread):
        self.log("ChangeToolTask")
        self.log('Changing the tool frame to {}.'.format(self.tool_name))
        self.robot.attached_tools['arm_0'].frame = self.tool_frame
        self.is_completed = True
        return True

class PickBrickURTask(URTask):
    def __init__(self, robot, robot_address, assembly=None, brick_key=None, grip=True, key=None):
        super(PickBrickURTask, self).__init__(robot, robot_address, key)
        self.robot = robot
        self.robot_address = robot_address
        self.assembly = assembly
        self.brick_key = brick_key
        self.grip = grip

    def urscript_fabrication_header(self):
        ## Initialize instance
        self.urscript = URScript_ParallelGrip(*self.robot_address)
        self.urscript.start()
        
        if self.robot:
            ## Set tool
            tool = self.robot.attached_tool
            self.urscript.set_tcp(list(tool.frame.point)+list(tool.frame.axis_angle_vector))
        self.urscript.textmessage(">> Starting TASK {}.".format(self.key), string=True)
        
        if self.server:
            self.urscript.set_socket(self.server.ip, self.server.port, self.server.name)
            self.urscript.socket_open(self.server.name)
            ## Send script received msg
            self.urscript.socket_send_line_string(self.rec_msg, self.server.name)
    
    def create_urscript(self):
        self.log("Picking started!")
        self.urscript.set_payload(1.2, [-0.005, 0.0, 0.052])
        self.urscript.parallelgrip_open()

        # Move down 1st try.
        self.urscript.move_force_mode(force_z=20.0, speed_z=0.015)
        self.urscript.stop_by_force(15.0)

        if self.assembly is not None:
            brick_frame = self.robot.from_WCF_to_RCF(self.assembly.part(self.brick_key).frame.transformed(Translation.from_vector(Vector.Zaxis()*0.0225)))
            brick_pose = brick_frame.point.__data__ + brick_frame.axis_angle_vector.__data__
            # Check the x force.
            self.urscript.add_line("complete_force = get_tcp_force()")
            self.urscript.add_line("x_force = complete_force[3]")
            self.urscript.add_lines(["textmsg(complete_force)"])
            self.urscript.add_lines(["textmsg(x_force)"])
            self.urscript.add_line("brick_pose = p[{}, {}, {}, {}, {}, {}]".format(*brick_pose))
            self.urscript.add_line("distance_taken = 0.001")
            # self.urscript.add_line("textmsg(brick_pose)")
            self.urscript.add_line("current_tcp_pose = get_actual_tcp_pose()")
            # self.urscript.add_line("textmsg(current_tcp_pose)")
            # self.urscript.add_line("textmsg(norm(brick_pose[2] - current_tcp_pose[2]))")
            self.urscript.add_line("last_move = 0")
            # # Check if in close 3 cm (in z axis), if not move around and try again.
            self.urscript.add_line("while norm(brick_pose[2] - current_tcp_pose[2]) > 0.037:", indent=1) # or distance_taken > 0.01
            # self.urscript.add_line("textmsg(norm(brick_pose[2] - current_tcp_pose[2]))", indent=2)

            self.urscript.add_line("pose_new = get_actual_tcp_pose()", indent=2)
            self.urscript.move_tool_by_distance(z_distance=-0.004, indent=2)
            self.urscript.add_line("sleep({})".format(1.0), indent=2)

            self.urscript.add_line("if x_force > 0:", indent=2)
            self.urscript.move_tool_by_distance(y_distance=-0.008, indent=3)
            self.urscript.add_line("last_move = -1", indent=3)
            self.urscript.add_line("else:", indent=2)
            self.urscript.move_tool_by_distance(y_distance=0.008, indent=3)
            self.urscript.add_line("last_move = 1", indent=3)
            self.urscript.add_line("end", indent=2)

            # Move down again.
            self.urscript.add_line("sleep({})".format(1.0), indent=2)
            self.urscript.move_force_mode(force_z=20.0, speed_z=0.015, indent=2)
            self.urscript.stop_by_force(15.0, indent=2)
            self.urscript.add_line("complete_force = get_tcp_force()",indent=2)
            self.urscript.add_line("x_force = complete_force[3]",indent=2)
            self.urscript.add_lines(["textmsg(complete_force)"], indent=2)
            self.urscript.add_lines(["textmsg(x_force)"], indent=2)

            self.urscript.add_line("pose_new_low = get_actual_tcp_pose()", indent=2)
            self.urscript.add_line("distance_taken = pose_dist(pose_new, pose_new_low)", indent=2)
            self.urscript.add_line("current_tcp_pose = get_actual_tcp_pose()", indent=2)

            self.urscript.add_line("end", indent=1)

        self.urscript.textmessage("Got the brick.", string=True)

        # Move up a little.
        self.urscript.move_tool_by_distance(z_distance=-0.003)
        self.urscript.add_line("sleep({})".format(2.0))

        if self.assembly is not None:
            # Move further in y direction.
            self.urscript.add_line("if last_move < 0:")
            self.urscript.move_tool_by_distance(y_distance=-0.008, indent=1)
            self.urscript.add_line("elif last_move > 0:")
            self.urscript.move_tool_by_distance(y_distance=0.008, indent=1)
            self.urscript.add_line("end", indent=1)

        # # Go in x to get a mid point.
        # self.urscript.move_force_mode(force_y=-10.0, speed_y=0.010)
        # self.urscript.stop_by_force(15.0)

        # # Go to middle.
        # self.urscript.add_line("sleep({})".format(1.0))
        # self.urscript.move_tool_by_distance(x_distance=0.0075)
        # self.urscript.add_line("sleep({})".format(1.0))

        # # Move down.
        # self.urscript.move_force_mode(force_z=15.0, speed_z=0.010)
        # self.urscript.stop_by_force(15.0)

        if self.grip:
            self.urscript.parallelgrip_close()

class PlaceBrickURTask(URTask):
    def __init__(self, robot, robot_address, release=True, key=None):
        super(PlaceBrickURTask, self).__init__(robot, robot_address, key)
        self.robot = robot
        self.robot_address = robot_address
        self.release = release

    def urscript_fabrication_header(self):
        ## Initialize instance
        self.urscript = URScript_ParallelGrip(*self.robot_address)
        self.urscript.start()
        
        if self.robot:
            ## Set tool
            tool = self.robot.attached_tool
            self.urscript.set_tcp(list(tool.frame.point)+list(tool.frame.axis_angle_vector))
        self.urscript.textmessage(">> TASK {}".format(self.key), string=True)
        
        if self.server:
            self.urscript.set_socket(self.server.ip, self.server.port, self.server.name)
            self.urscript.socket_open(self.server.name)
            ## Send script received msg
            self.urscript.socket_send_line_string(self.rec_msg, self.server.name)
                
    def create_urscript(self):
        self.log("Placing started!")
        self.urscript.set_payload(3.8, [-0.005, 0.0, 0.115])

        self.urscript.parallelgrip_close()

        self.urscript.add_line("\tsleep({})".format(1.0))

        self.urscript.move_force_mode(force_z=50.0, speed_z=0.03)
        self.urscript.stop_by_force(20.0)

        if self.release:
            self.urscript.parallelgrip_open()
        
        self.urscript.set_payload(1.2, [-0.005, 0.0, 0.052])
        self.urscript.move_tool_by_distance(z_distance=-0.1, velocity=0.1, radius=0.01)
        self.urscript.parallelgrip_close()

class UpdateAssemblyAttributes(Task):
    def __init__(self, assembly, brick_key, attributes={"built":False, "pick_key":0}, key=None):
        super(UpdateAssemblyAttributes, self).__init__(key)
        self.assembly = assembly
        self.brick_key = brick_key
        self.attributes = attributes
    
    def update_neighbor_availability(self, assembly, part_key=None):
        updated_keys = []
        # Determine which parts to check
        part_keys = (
            assembly.graph.neighbors_out(part_key)
            if part_key is not None
            else assembly.part_keys()
        )
        for key in part_keys:
            below = assembly.graph.neighbors_in(key)
            below_built = all(
                bool(assembly.graph.node_attribute(n, "built")) for n in below
            )

            if below_built and not assembly.graph.node_attribute(key, "available"):
                assembly.graph.node_attribute(key, "available", True)
                updated_keys.append(key)
        return updated_keys

    def run(self, stop_thread):
        # Change brick attributes:
        for attribute, value in self.attributes.items():
            self.assembly.graph.node_attribute(self.brick_key, attribute, value)
        self.is_completed = True
        return True

# Marker perception tasks.

class ScanMarkersTask(Task):
    def __init__(self, robot, marker_ids=["marker_0"], reference_frame_id="base", key=None):
        super(ScanMarkersTask, self).__init__(key)
        self.robot = robot
        self.marker_ids = marker_ids
        self.reference_frame_id = reference_frame_id

    def get_detected_markers(self, stop_thread):
        self.log("Scanning markers...")
        marker_dict = {}

        for marker_id in self.marker_ids:
            self.log('Receiving the frame for marker: {}'.format(marker_id))
            pose = None

            self.robot.mobile_client.clean_tf_frame()
            time.sleep(0.5)
            self.robot.mobile_client.tf_subscribe(str(marker_id), self.reference_frame_id)

            time_limit = 10
            start_time = time.time()
            left_time = 10
            # Wait until pose is received.
            while not stop_thread() and left_time > 0:
                if self.robot.mobile_client.tf_frame is not None:
                    pose = Frame(self.robot.mobile_client.tf_frame.point, 
                                    Vector(self.robot.mobile_client.tf_frame.xaxis.x,self.robot.mobile_client.tf_frame.xaxis.y),
                                    Vector(self.robot.mobile_client.tf_frame.yaxis.x, self.robot.mobile_client.tf_frame.yaxis.y)) # Correcting to the ground.
                    break
                time.sleep(0.1)
                left_time = time_limit - (time.time() - start_time)

            if pose is None:
                self.log('For marker with id {}, could not get the frame.'.format(marker_id))
            else:
                marker_dict[marker_id] = pose
                self.log('For marker with id {}, got the pose: {}'.format(marker_id, pose))
    
            self.robot.mobile_client.tf_unsubscribe(str(marker_id), self.reference_frame_id)

        self.log("Scanning completed.")

        return marker_dict

    def run(self, stop_thread):
        marker_dict = self.get_detected_markers(stop_thread)
        self.log(marker_dict)
        self.is_completed = True
        return True

class ScanStackMarkerTask(ScanMarkersTask):
    def __init__(self, robot, assembly, stack_marker_id="marker_1", position=0, key=None):
        super(ScanStackMarkerTask, self).__init__(robot, marker_ids=[stack_marker_id], reference_frame_id="base", key=key)
        self.robot = robot
        self.assembly = assembly
        self.stack_marker_id = stack_marker_id
        self.position = 0

    def run(self, stop_thread):
        marker_dict = self.get_detected_markers(stop_thread)
        marker_frame = marker_dict[self.stack_marker_id]
        marker_frame_WCF = self.robot.from_RCF_to_WCF(marker_frame)

        if "marker_frames_WCF" not in self.assembly.graph.attributes:
            self.assembly.graph.attributes["marker_frames_WCF"] = {}

        self.assembly.graph.attributes["marker_frames_WCF"][str(self.position)] = marker_frame_WCF

        self.is_completed = True
        return True

class GlobalMarkerTask(ScanMarkersTask):
    def __init__(self, robot, key=None):
        super(GlobalMarkerTask, self).__init__(robot, marker_ids=["marker_0"], reference_frame_id="base", key=key)
        self.robot = robot

    def run(self, stop_thread):
        marker_dict = self.get_detected_markers(stop_thread)
        marker_frame = marker_dict["marker_0"]
        marker_frame_BCF = self.robot.from_RCF_to_BCF(marker_frame)
        BCF_in_marker = Frame.from_transformation(
                Transformation.from_frame(marker_frame_BCF).inverted()
            )
        self.log(BCF_in_marker)

        self.robot.BCF_slam = BCF_in_marker
        self.robot._record_state("BCF_slam")

        self.is_completed = True
        return True

# Brick perception tasks.

class TriggerEstimationTask(Task):
    def __init__(self, robot, trigger=True, cuda_off=False, sleep=0, key=None):
        super(TriggerEstimationTask, self).__init__(key)
        self.robot = robot
        self.trigger = trigger
        self.cuda_off = cuda_off
        self.sleep = sleep
        
    def run(self, stop_thread):
        self.log('Estimation is set to {}!'.format(self.trigger))
        if self.cuda_off:
            service_name = '/trigger_pose_complete'
        else:
            service_name = '/trigger_pose'

        while not stop_thread():
            if self.robot.mobile_client.is_service_available(service_name):
                result = self.robot.mobile_client.service_call(service_name, 'std_srvs/SetBool', {'data': self.trigger})
                success = result['success']
                message = result['message']
                self.log('Activation message: {}'.format(message))
                if success:
                    break
            else:
                self.log("Trigger for estimation service is not available.")
                break
            time.sleep(0.1)

        self.log("Sleeping for {} seconds...".format(str(self.sleep)))
        time.sleep(self.sleep)

        self.is_completed = True
        return True

class CleanBricksTask(Task):
    def __init__(self, robot, key=None):
        super(CleanBricksTask, self).__init__(key)
        self.robot = robot
        
    def run(self, stop_thread):
        self.log('CleanBricksTask')
        service_name = '/clean_bricks'

        while not stop_thread():
            if self.robot.mobile_client.is_service_available(service_name):
                result = self.robot.mobile_client.service_call(service_name, 'std_srvs/SetBool', {'data': True})
                success = result['success']
                message = result['message']
                self.log('Activation message: {}'.format(message))
                if success:
                    break
            else:
                self.log("Clean bricks service is not available.")
                break
            time.sleep(0.1)

        self.is_completed = True
        return True

class ScanBricksTask(Task):
    def __init__(self, robot, reference_frame_id="base", key=None):
        super(ScanBricksTask, self).__init__(key)
        self.robot = robot
        self.reference_frame_id = reference_frame_id

    def get_detected_bricks(self, stop_thread):
        self.log("Scanning bricks...")
        brick_dict = {}

        # Ask for estimated brick ids.
        while not stop_thread():
            self.log('Asking for the brick amount...')
            result = self.robot.mobile_client.service_call('/brick_amount', 'std_srvs/SetBool', {'data': True})
            if result['success']:
                brick_amount = int(result['message'])
                self.log("Brick amount is {}".format(brick_amount))
                break
            time.sleep(0.1)

        brick_list = [i for i in range(brick_amount)]

        # One by one get the frames of the bricks in the list.
        if len(brick_list) == 0:
            self.log('No bricks estimated.')
        else:
            for brick_id in brick_list:
                self.log('Receiving the frame for brick: {}'.format(brick_id))
                pose = None

                self.robot.mobile_client.clean_tf_frame()
                time.sleep(0.5)
                self.robot.mobile_client.tf_subscribe("brick_" + str(brick_id), self.reference_frame_id)

                time_limit = 10
                start_time = time.time()
                left_time = 10
                # Wait until pose is received.
                while not stop_thread() and left_time > 0:
                    if self.robot.mobile_client.tf_frame is not None:
                        pose = Frame(self.robot.mobile_client.tf_frame.point, 
                                        Vector(self.robot.mobile_client.tf_frame.xaxis.x,self.robot.mobile_client.tf_frame.xaxis.y),
                                        Vector(self.robot.mobile_client.tf_frame.yaxis.x, self.robot.mobile_client.tf_frame.yaxis.y)) # Correcting to the ground.
                        # Force brick frames to be same direction - xaxis to the robot.
                        if pose.zaxis.z > 0:
                            pose = pose.transformed(Rotation.from_axis_and_angle(pose.yaxis, math.radians(180), pose.point))
                        if pose.yaxis.x > 0:
                            pose = pose.transformed(Rotation.from_axis_and_angle(pose.zaxis, math.radians(180), pose.point))
                        break
                    time.sleep(0.1)
                    left_time = time_limit - (time.time() - start_time)

                if pose is None:
                    self.log('For brick with id {}, could not get the frame.'.format(brick_id))
                else:
                    # Transform to BCF_slam.
                    brick_dict[brick_id] = pose
                    self.log('For brick with id {}, got the pose: {}'.format(brick_id, pose))
        
                self.robot.mobile_client.tf_unsubscribe("brick_" + str(brick_id), self.reference_frame_id)

        self.log("Scanning completed.")

        return brick_dict

    def run(self, stop_thread):
        brick_dict = self.get_detected_bricks(stop_thread)
        self.is_completed = True
        return True
    
class ScanSingleBrickAddNewTask(ScanBricksTask):
    def __init__(self, robot, assembly, brick_key_to_update, average=False, key=None):
        super(ScanSingleBrickAddNewTask, self).__init__(robot, key=key)
        self.assembly = assembly
        self.brick_key_to_update = brick_key_to_update
        self.average = average

        self.brick_shape = Box(xsize=0.24, ysize=0.115, zsize=0.045)

    def find_next_available_key(self, assembly):
        s = set([p for p in assembly.part_keys()])
        i = 1
        while i in s:
            i += 1
        return i

    def run(self, stop_thread):
        brick_dict = self.get_detected_bricks(stop_thread)

        self.log("Updating only the brick {}...".format(self.brick_key_to_update))

        for brick_id, pose in brick_dict.items():
            pose = self.robot.from_RCF_to_WCF(pose) 
            
            target_key = None
            # Compare the pose to each pose in assembly by seeing the distance.
            closest_distance = 0.1
            for key in self.assembly.graph.nodes_where({"built": True}):
                distance = distance_point_point(self.assembly.part(key).frame.point, pose.point)
                if distance < closest_distance:
                    self.log("Distance is {}".format(distance))
                    self.log("Brick {} is the same as id {}".format(key, brick_id))
                    closest_distance = distance
                    target_key = key
                    
            # Create a new element.
            if target_key is None:
                # Create *new* brick entry.
                key = self.find_next_available_key(self.assembly) 
                brick = Part()
                brick.shape = self.brick_shape
                brick.mesh = Mesh.from_shape(self.brick_shape)
                brick.frame = pose.copy()
                self.assembly.add_part(
                    brick,
                    key=key,
                    estimated_frame=pose.copy(),
                    initial_estimated_frame=pose.copy(),
                    available=True,
                    built=True
                )

                self.log("Creating a new brick key {} with frame {}".format(key, pose))

            # dist = distance_point_point(self.assembly.part(self.brick_key_to_update).frame.point, pose.point)
            # if dist < closest_distance:
            #     closest_distance = dist
            #     target_key = brick_id

            elif target_key == self.brick_key_to_update:
                self.log("Updating the pose of the brick key {} with id {}".format(self.brick_key_to_update, brick_id))

                if self.average:
                    current_pose = self.assembly.part(self.brick_key_to_update).frame
                    # find average:
                    average_pose = average_frame(current_pose, pose)
                    pose = average_pose
                    pose_BCF = self.robot.from_WCF_to_BCF(pose)
                    self.log("I took average.")

                part = self.assembly.part(self.brick_key_to_update)
                part.frame = pose.copy()
                self.assembly.graph.node_attribute(self.brick_key_to_update, 'estimated_frame', pose.copy())
            else:
                self.log("Not updating existing bricks other than {}.".format(self.brick_key_to_update))
                
        self.is_completed = True
        return True

class ScanAllBricksTask(ScanBricksTask):
    def __init__(self, robot, assembly, key=None):
        super(ScanAllBricksTask, self).__init__(robot, key=key)
        self.assembly = assembly
        self.brick_shape = Box(xsize=0.24, ysize=0.115, zsize=0.045)
    
    def find_next_available_key(self, assembly):
        s = set([p for p in assembly.part_keys()])
        i = 0
        while i in s:
            i += 1
        return i

    def run(self, stop_thread):
        time.sleep(2)
        brick_dict = self.get_detected_bricks(stop_thread)
        self.log("Registering all bricks...")

        for brick_id, pose in brick_dict.items():
            pose = self.robot.from_RCF_to_WCF(pose) 
            target_key = None
            # Compare the pose to each pose in assembly by seeing the distance.
            closest_distance = 0.05
            for key in self.assembly.graph.nodes():
                distance = distance_point_point(self.assembly.part(key).frame.point, pose.point)
                if distance < closest_distance:
                    self.log("Distance is {}".format(distance))
                    self.log("Brick {} is the same as id {}".format(key, brick_id))
                    closest_distance = distance
                    target_key = key
                    
            # Create a new element.
            if target_key is None:
                # Create *new* brick entry.
                key = self.find_next_available_key(self.assembly)
                brick = Part()
                brick.shape = self.brick_shape
                brick.mesh = Mesh.from_shape(self.brick_shape)
                brick.frame = pose.copy()
                self.assembly.add_part(
                    brick,
                    key=key,
                    estimated_frame=pose.copy(),
                    initial_estimated_frame=pose.copy(),
                )

                self.log("Creating a new brick key {} with frame {}".format(key, pose))
                self.assembly.graph.node_attribute(key, 'available', True)
                self.assembly.graph.node_attribute(key, 'built', True)

            elif target_key is not None:
                self.log("Updating the pose of the brick key {}".format(target_key))
                # Update existing element.
                self.assembly.find_by_key(target_key).frame = pose.copy()
                self.assembly.graph.node_attribute(target_key, 'estimated_frame', pose.copy())
                self.assembly.graph.node_attribute(target_key, 'initial_estimated_frame', pose.copy())
                        
        self.log("Registered all bricks...")
        self.is_completed = True
        return True

class ScanSingleBrickTask(ScanBricksTask):
    def __init__(self, robot, assembly, brick_key_to_update, frame_attribute=None, average=False, key=None):
        super(ScanSingleBrickTask, self).__init__(robot, key=key)
        self.assembly = assembly
        self.brick_key_to_update = brick_key_to_update
        self.frame_attribute = frame_attribute
        self.average = average

        self.brick_shape = Box(xsize=0.24, ysize=0.115, zsize=0.045)
    
    def slerp_quat(self, q1, q2, t):
        q1 = q1 / np.linalg.norm(q1)
        q2 = q2 / np.linalg.norm(q2)
        dot = np.dot(q1, q2)
        if dot < 0.0:
            q2 = -q2
            dot = -dot
        if dot > 0.9995:
            q = q1 + t * (q2 - q1)
            return q / np.linalg.norm(q)
        theta_0 = np.arccos(dot)
        theta = theta_0 * t
        q3 = q2 - q1 * dot
        q3 = q3 / np.linalg.norm(q3)
        return q1 * np.cos(theta) + q3 * np.sin(theta)

    def average_frame(self, frame_a, frame_b):
        # --- Average position ---
        p = Point(
            0.5 * (frame_a.point.x + frame_b.point.x),
            0.5 * (frame_a.point.y + frame_b.point.y),
            0.5 * (frame_a.point.z + frame_b.point.z),
        )

        # --- Average orientation via SLERP ---
        R_a = Rotation.from_frame(frame_a)
        R_b = Rotation.from_frame(frame_b)

        qa = np.array(R_a.quaternion)
        qb = np.array(R_b.quaternion)

        q_avg = self.slerp_quat(qa, qb, 0.5)
        R_avg = Rotation.from_quaternion(q_avg)

        # --- Build averaged frame ---
        avg_frame = Frame.from_rotation(R_avg)
        avg_frame.point = p
        return avg_frame

    def run(self, stop_thread):
        brick_dict = self.get_detected_bricks(stop_thread)

        self.log("Updating only the brick {}...".format(self.brick_key_to_update))

        for brick_id, pose in brick_dict.items():
            pose = self.robot.from_RCF_to_WCF(pose) 
            
            target_key = None
            # Compare the pose to each pose in assembly by seeing the distance.
            closest_distance = 0.1
            for key in self.assembly.graph.nodes_where({"built": True}):
                distance = distance_point_point(self.assembly.part(key).frame.point, pose.point)
                if distance < closest_distance:
                    self.log("Distance is {}".format(distance))
                    self.log("Brick {} is the same as id {}".format(key, brick_id))
                    closest_distance = distance
                    target_key = key

        # Update pose
        if target_key == self.brick_key_to_update:
            self.log("Updating the pose of the brick key {} with id {}".format(self.brick_key_to_update, brick_id))

            if self.average:
                current_pose = self.assembly.part(self.brick_key_to_update).frame
                # find average:
                average_pose = self.average_frame(current_pose, pose)
                pose = average_pose
                pose_BCF = self.robot.from_WCF_to_BCF(pose)
                self.log("I took average.")

            part = self.assembly.part(self.brick_key_to_update)
            part.frame = pose.copy()
            self.assembly.graph.node_attribute(self.brick_key_to_update, 'estimated_frame', pose.copy())
        else:
            self.log(f"No match found for brick {self.brick_key_to_update}")
                
        self.is_completed = True
        return True
    
# Camera image task.

class ReceiveCameraImageTask(Task):
    def __init__(self, robot, brick_key=0, view="A", stack_key=0, data_path="C:/Users/saral/workspace/projects/workshop_iaac_2026/data/images_evaluation", key=None):
        super(ReceiveCameraImageTask, self).__init__(key)
        self.robot = robot
        self.brick_key = brick_key
        self.view = view
        self.data_path = data_path
        self.stack_key = stack_key
        self.img_msg = None
    
    def _receive_message(self, message):
        if self.img_msg is None:
            self.img_msg = message
            self.log("Received image msg.")

    def run(self, stop_thread):
        self.log('Receiving the view {} for brick {}!'.format(self.view, self.brick_key))
        self.log("Sleeping for 4 seconds.")
        time.sleep(4)

        while not stop_thread():
            self.robot.mobile_client.topic_subscribe(
                "/camera/camera/color/image_raw", "sensor_msgs/msg/Image", self._receive_message
            )
            if self.img_msg is not None:
                break
            time.sleep(0.1)

        self.robot.mobile_client.topic_unsubscribe("/camera/camera/color/image_raw")

        DATA = os.path.abspath(self.data_path)
        PATH = os.path.join(DATA, "stack{}_brick{}_view{}.npy".format(self.stack_key, self.brick_key, self.view))
        self.log(PATH)
        np.save(PATH, self.img_msg)
        self.log("Saved image msg.")

        self.is_completed = True
        return True
