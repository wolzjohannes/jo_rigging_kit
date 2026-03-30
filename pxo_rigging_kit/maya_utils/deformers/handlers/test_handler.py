from maya.api import OpenMaya as om2

class IOCallbacks:
    def __init__(self, main_progress=None, sub_progress=None, message=None):
        self.main_progress = main_progress
        self.sub_progress = sub_progress
        self.message = message




class IOHandler:
    """
    Replace the simulated work with real OpenMaya / cmds operations.
    """

    def __init__(self, items):
        self.items = items
        self.index = 0
        self.substep = 0
        self.cancel_requested = False

        self._assert_main_thread()

    def request_cancel(self):
        self.cancel_requested = True

    def has_more_work(self):
        return self.index < len(self.items)

    def run_step(self, callbacks: IOCallbacks):

        self._assert_main_thread()

        if not self.classes_to_work_with:
            callbacks.message("Initializing operators...")
            self.initialize_operators_for_objects()
            return True

        if self.cancel_requested:
            if callbacks.message:
                callbacks.message("Operation cancelled.")
            return False

        if not self.has_more_work():
            if callbacks.message:
                callbacks.message("All operations completed.")
            return False

        total_amount = len(self.classes_to_work_with)

        for i, op in enumerate(self.classes_to_work_with):

            pct = int(((i + 1) / total_amount) * 100)

            callbacks.sub_progress(pct, f"Importing {op.deformer_operator_name}")
            op.gather_scene_external_data()

            callbacks.sub_progress(pct, f"Importing {op.deformer_operator_name}")
            op.import_data()

            callbacks.main_progress(main_pct, f"Processing {op.deformer_operator_name}")

            main_pct = int((self.index / total_amount * 100))

        return self.has_more_work()

    def _assert_main_thread(self):
        """
        This is the safest and most reliable main-thread check in Maya.
        If this function throws, you are NOT on the main thread.
        """
        try:
            # This is guaranteed main-thread only
            om2.MGlobal.getActiveSelectionList()
        except Exception as e:
            raise RuntimeError(
                "OpenMaya 2.0 call failed — importer is NOT running on the main thread.\n"
                "Error: {}".format(e)
            )

    def _test_mfnmesh_creation(self, item_name):
        """
        Safe, minimal MFnMesh creation.
        If this runs without crashing, we are on the main thread.
        """

        # Define 3 vertices
        points = [
            om2.MPoint(0, 0, 0),
            om2.MPoint(1, 0, 0),
            om2.MPoint(0, 1, 0)
        ]

        # One triangle face
        face_counts = [3]
        face_connects = [0, 1, 2]

        # Create the mesh
        mesh_fn = om2.MFnMesh()
        mesh_obj = mesh_fn.create(
            points,
            face_counts,
            face_connects
        )

        # Name it
        mesh_fn.setName("{}_testMesh".format(item_name))

        # Return something useful
        return mesh_fn.name()

