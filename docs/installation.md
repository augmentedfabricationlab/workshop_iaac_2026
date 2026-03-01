---
layout: page
title: Installation
---

### Requirements

* Rhino 8 / Grasshopper

### Installation

#### Installation of COMPAS FAB on Rhino

1. If this is your first time, open Rhino and Grasshopper, then create a *Python 3 Script* block. This will load your Python path. Now you can close Rhino.

2. Find your Rhino Python path, which should look like this: *C:\Users\your_user_name\.rhinocode\py39-rh8\python.exe*

3. Replace the path below with your path and run:

    ```bash
    C:\Users\your_user_name\.rhinocode\py39-rh8\python.exe -m pip install compas_fab
    ```

#### Installation of Google GenAI on Rhino

1. Similar to above, replace the path below with your path and run:

    ```bash
    C:\Users\your_user_name\.rhinocode\py39-rh8\python.exe -m pip install google-genai
    ```

#### Installation of GitHub repositories

1. Create a workspace/projects folder by opening a terminal (recommended)

    ```text
    cd %USERPROFILE%
    mkdir -p workspace/projects && cd workspace/projects
    ```

    This will create:

    `Users/your_user_name/workspace/projects`

2. Clone the current repository

    ```text
    git clone https://github.com/augmentedfabricationlab/workshop_iaac_2026.git
    ```

3. Clone the assembly_information_model repository, go to the folder, and switch to the compas2 branch

    ```text
    git clone https://github.com/augmentedfabricationlab/assembly_information_model.git
    cd assembly_information_model
    git checkout compas2
    ```

4. Verify

    ```text
    git branch
    ```

    You should see `compas2` selected.

5. Source the assembly_information_model in Rhino

    In Grasshopper, double-click any *Python 3 Script* block, go to **Tools** in the top menu, then **Options**. Open the **Python 3** tab and in **Module search paths** add:

    `C:\Users\your_user_name\workspace\projects\assembly_information_model\src`
