# Robotic Disassembly & Reassembly with Spatial Artificial Intelligence

## Workshop IAAC 2-6 March 2026

### Requirements

* Windows 10 Professional
* Rhino 8 / Grasshopper
* [Anaconda Python](https://www.anaconda.com/download)
* [Visual Studio Code](https://code.visualstudio.com/)

### Installation

#### Installation COMPAS FAB
    
    (base)  conda create -n your_env_name -c conda-forge compas_fab
    (base)  conda activate your_env_name

#### Verify Installation of COMPAS FAB

    (your_env_name) python -m compas_fab
    Yay! COMPAS FAB is installed correctly!   

#### Installation of COMPAS FAB on Rhino from PyPI

    (your_env_name) python -m compas_rhino.print_python_path
    (your_env_name) C:\Users\your_user_name\.rhinocode\py39-rh8\python.exe -m pip install compas_fab

#### Installation of assembly information model

1. Create a Workspace Folder (Recommended)

Open a terminal or Anaconda Prompt:

    cd %USERPROFILE%
    mkdir workspace
    cd workspace

This will create:

    Users/your_user_name/workspace

2. Clone the Repository

        git clone https://github.com/augmentedfabricationlab/assembly_information_model.git
        cd assembly_information_model

3. Switch to the compas2 branch

        git checkout compas2

Verify:

    git branch

You should see compas2 selected.

4. Activate Your Conda Environment

       conda activate your_env_name

5️. Install Development Dependencies

Install the project in editable mode:

    pip install -e .

6. Find the Rhino 8 Python Executable

Run:

    python -m compas_rhino.print_python_path


You should see something like:

    C:\Users\your_user_name\.rhinocode\py39-rh8\python.exe

Copy this full path.

7. Install the Repository into Rhino 8

Use the Rhino Python executable to install the package:

    C:\Users\your_user_name\.rhinocode\py39-rh8\python.exe -m pip install -e C:\Users\your_user_name\workspace\assembly_information_model

✅ Final Check

Open Rhino 8 → Python and run:

    import assembly_information_model

If no errors appear, the installation is successful.

Credits
-------------

This package was created by Begüm Saral <saral.begum@gmail.com> `@begums <https://github.com/begums>`_ at `@augmentedfabricationlab <https://github.com/augmentedfabricationlab>`_
