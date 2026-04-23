import os
import numpy as np

from asimov.base.common import get_safe_path
from asimov import conf
from asimov.io import echo

_loaded_set = None
_loaded_set_name = None


def is_loaded(set_name):
    if _loaded_set is not None and _loaded_set_name == set_name:
        return True
    return False


def load(basedir=None, set_name=None) -> bool:
    if basedir is None:
        basedir = conf.CONF["PLAYINGCARD"].get("BASEDIR", "$HOME/projects/playingcarddata")
    if set_name is None:
        set_name = conf.CONF["PLAYINGCARD"].get("SET_NAME", "bicycle")

    basedir = os.path.expandvars(os.path.expanduser(basedir))

    # 1. compose absolute path to npz file given set_name
    try:
        npz_path = get_safe_path(
            basedir, f"templates_{set_name}_archive.npz", must_exist=True
        )
    except FileNotFoundError:
        return False

    ##    echo(f"{{labelcolor}}Loading templates and metadata from: {{valuecolor}}{npz_path}{{reset}}")

    # 2. load template data
    try:
        data = np.load(npz_path, allow_pickle=True)
    except FileNotFoundError:
        echo(
            f"{{red}}{{crossmark}} {{labelcolor}}file {{valuecolor}}{npz_path}{{labelcolor}} not found"
        )
        return False

    # 3. Extract the metadata array and convert it to a Python dictionary
    if "__metadata__" not in data.files:
        raise KeyError("NPZ file is missing the required '__metadata__' entry.")

    metadata_dict = data["__metadata__"].item()

    # 4. Extract the set_name from the dictionary
    set_name_key = "__set_name__"
    if set_name_key not in metadata_dict:
        raise KeyError(f"Metadata is missing the required '{set_name_key}' key.")

    extracted_set_name = metadata_dict[set_name_key]

    # 5. Assign to global variables
    _loaded_set = data
    _loaded_set_name = extracted_set_name

    ##    echo(f"{{checkmark}}{{labelcolor}} Successfully loaded set: {{valuecolor}}'{set_name}'{{reset}}")
    return True


def save(basedir=None, set_name=None, filename=None) -> bool:
    """
    Saves the currently loaded playing card set data (from _loaded_set) to a new NPZ file.

    Args:
        basedir (str): The directory where the new NPZ file will be saved.
        set_name (str): Card set name.
        filename (Optional[str]): An optional specific filename (e.g., 'backup.npz').
                                  If None, the default naming convention is used.

    Returns:
        bool: True if save succeeded, False otherwise.
    """
    global _loaded_set, _loaded_set_name

    if basedir is None:
        basedir = conf.CONF["PLAYINGCARD"].get("BASEDIR", "$HOME/projects/playingcarddata")
    if set_name is None:
        set_name = _loaded_set_name or conf.CONF["PLAYINGCARD"].get("SET_NAME", "bicycle")

    if _loaded_set is None:
        echo(
            "{warning}️ No card set is currently loaded in memory (_loaded_set is None). Cannot save."
        )
        return False

    # Determine the final filename
    if filename is None:
        filename = f"templates_{set_name}_archive.npz"

    # Use the safe path utility for the output path
    try:
        # Ensure basedir exists before attempting to write
        output_path = get_safe_path(basedir, filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        echo(
            f"{{labelcolor}}Saving loaded set to: '{{valuecolor}}{output_path}{{labelcolor}}'{{reset}}",
            end="",
        )

        # 1. Prepare data for saving
        # npz_data must be a dictionary of {name: array} arguments
        npz_data = {}

        # NOTE: np.load() returns a container that holds file handles.
        # We must explicitly read each array to copy its data before saving it again.

        # 2. Iterate through all keys in the loaded set and copy the array data
        for key in _loaded_set.files:
            # When accessing data[key], numpy reads the array from disk
            npz_data[key] = _loaded_set[key]

        # 3. Save the prepared data to the new file
        np.savez_compressed(output_path, **npz_data)

        echo("{checkmark}OK - {pluralize(len(npz_data), 'arrray', 'arrays')}")
        return True

    except Exception as e:
        echo("[FAIL]")
        raise e


def get_metadata():
    """
    Returns the metadata dictionary of the currently loaded set, or None if no set is loaded.
    """
    if _loaded_set is None:
        return None

    # The metadata is stored under the key '__metadata__' as a single item/array.
    if "__metadata__" in _loaded_set.files:
        # .item() converts the 0-d array back into the original Python dictionary
        return _loaded_set["__metadata__"].item()
    return None
