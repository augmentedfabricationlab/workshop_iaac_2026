---
layout: default
title: About
---

# About

This workshop explores how robotic disassembly and reassembly can support repair, reuse, and circular construction through Spatial AI. We focus on reclaimed brickwork as a representative building system that is widely available, modular, and historically central to architectural reconstruction.

Across five days at IAAC in Barcelona (March 2 to 6, 2026), participants will work with a mobile manipulation setup to capture a scene, detect and track objects, generate a digital twin, and execute robotic manipulation for disassembly and reassembly. Along the way, we investigate how to extract and store material knowledge from each brick and how to reuse that knowledge to inform a new design.

<figure>
  <img src="{{ '/images/title_img_2.png' | relative_url }}"
       alt="Robotic Disassembly & Reassembly with Spatial AI."
       style="width:100%"
       class="center">
  <figcaption>Robotic Disassembly and Reassembly with Spatial AI. The workshop connects scene perception, object understanding, and robotic manipulation with design exploration.</figcaption>
</figure>

The workshop builds on current research in robotic deconstruction enabled by spatial artificial intelligence and extends it toward a full pipeline from disassembly to reassembly. Starting from a manually built brick assembly, the robot disassembles the structure while perception systems record geometry, pose, and object identities. Based on this data, we introduce material knowledge extraction to describe the state of each brick, for example surface changes, damage, and visual features. This structured information then becomes a design input for reassembly.

Participants will develop a disassembly to reassembly workflow that connects four layers:
scene level perception and fiducial world tracking
object level perception and digital twin generation
robot manipulation for picking, placing, and reassembly
multimodal AI supported design exploration using textual prompts and sketches to propose new assemblies that respect the extracted material knowledge

The technical setup includes a UR10e robot arm mounted on a Husky mobile base, multiple Intel RealSense D435i cameras (fixed and end effector), and two end effectors (vacuum and parallel gripper). A high performance workstation with Ubuntu 22 and ROS Humble or Jazzy is used to run perception and manipulation. The material basis for the workshop is a reclaimed brick stack of roughly 100 bricks with dimensions 24 x 11.5 x 5.2 cm.

Deliverables are produced in groups and include documentation of the perception pipeline, digital twin outputs, manipulation strategies, extracted material attributes, and AI supported design studies. Results can be presented as drawings, digital models, and images that demonstrate the full loop from disassembly to reassembly.

Workshop team: Begüm Saral, Tizian Rein, Kathrin Dörfler.
