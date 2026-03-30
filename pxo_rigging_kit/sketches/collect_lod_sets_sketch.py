def assemble_rig_lod_task_name(lod_number):
    """Assemble the rig lod task name for the current asset.

    Args:
        lod_number(str): The rig lod number.

    Returns:
        str: The cam_master task name for the current shot.

    """
    naming_rig_data = {
        "task_type": "rig",
        "task_name": lod_number,
    }
    return pixo_naming.get("sg_asset_task", naming_rig_data)


def get_rig_lod_sgid(lod_number):
    """Get the task sgid of the rig lod of the current asset context.

    Args:
        lod_number(str): The rig lod number.

    Notes:
        In case no such rig lod task exists in Shotgun for the current asset context
        then we insist to create it because we need a rig lod task to link to in
        upcoming plugins.

    Returns:
        int: The task sgid of the rig task of the current asset context.

    """
    shotgun = sg_utils.get_shotgun_connection("blablabla")

    project = {"type": "Project", "id": int(os.environ["PXO_PROJECT_SGID"])}
    rig_lod_task_name = assemble_rig_lod_task_name(lod_number)

    filters = [
        [
            "project",
            "is",
            project,
        ],
        ["content", "is", rig_lod_task_name],
        ["entity", "is", {"type": "Asset", "id": int(os.environ["PXO_ASSET_SGID"])}],
    ]
    query = shotgun.find_one("Task", filters)

    # There might be situations when a shot does not have a cam_master task, yet. In
    # that case we insist to create such a task because we need it in upcoming plugins
    # because we need to link to this task, so it must exist. To make sure this works
    # for every session, we need to connect using a script-key that holds sufficient
    # permissions to create tasks. Not all users have that permission.
    if not query:
        query = create_rig_lod_task(project, rig_lod_task_name, shotgun, lod_number)

    return query["id"]


def create_rig_lod_task(project, rig_lod_task_name, shotgun, lod_number):
    """Create a rig lod task for the current asset context.

    Args:
        project (dict): Type mapping of the current project in the format:
            {
                "type": "Project",
                "id": <SGID of current project>
            }
        rig_lod_task_name (str): The camera task name to use for the task that
            gets created.
        shotgun (shotgun_api3.shotgun.Shotgun): Shotgun connection to communicate with
            Shotgun.
        lod_number(str): The rig lod number.

    Returns:
        dict: The information of the task that got created.

    """
    task_creation_data = {
        "project": project,
        "content": rig_lod_task_name,
        "entity": {"type": "Asset", "id": int(os.environ["PXO_ASSET_SGID"])},
        "sg_task_type": {"type": "CustomNonProjectEntity05", "id": 22},
        "sg_task_part_name": lod_number,
    }
    return shotgun.create("Task", task_creation_data)