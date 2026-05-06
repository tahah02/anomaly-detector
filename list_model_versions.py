import json
import os
from backend.mlops.model_versioning import get_versioning

def list_versions():
    versioning = get_versioning()
    current_version = versioning.get_current_version()
    available_versions = versioning.list_versions()
    
    versions_data = []
    
    current_dir = os.getcwd()
    base_dir = current_dir
    
    if os.path.basename(current_dir) == "ConfigManagementUI":
        base_dir = os.path.dirname(current_dir)
    
    while not os.path.exists(os.path.join(base_dir, "backend")) and base_dir != os.path.dirname(base_dir):
        base_dir = os.path.dirname(base_dir)
    
    isolation_forest_path = os.path.join(base_dir, "backend", "model", "isolation_forest.pkl")
    autoencoder_path = os.path.join(base_dir, "backend", "model", "autoencoder.h5")
    
    base_version_info = {
        "version": "base",
        "is_active": current_version == "base" or current_version == "1.0.0",
        "has_isolation_forest": os.path.exists(isolation_forest_path),
        "has_autoencoder": os.path.exists(autoencoder_path),
        "isolation_forest_metadata": {
            "model_type": "isolation_forest",
            "version": "base",
            "description": "Original trained model"
        },
        "autoencoder_metadata": {
            "model_type": "autoencoder",
            "version": "base",
            "description": "Original trained model"
        }
    }
    versions_data.append(base_version_info)
    
    for version in available_versions:
        version_info = {
            "version": version,
            "is_active": version == current_version,
            "has_isolation_forest": False,
            "has_autoencoder": False,
            "isolation_forest_metadata": None,
            "autoencoder_metadata": None
        }
        
        if_metadata = versioning.get_version_metadata(version, "isolation_forest")
        if if_metadata:
            version_info["has_isolation_forest"] = True
            version_info["isolation_forest_metadata"] = if_metadata
        
        ae_metadata = versioning.get_version_metadata(version, "autoencoder")
        if ae_metadata:
            version_info["has_autoencoder"] = True
            version_info["autoencoder_metadata"] = ae_metadata
        
        versions_data.append(version_info)
    
    result = {
        "success": True,
        "current_version": current_version if current_version else "base",
        "total_versions": len(versions_data),
        "versions": versions_data
    }
    
    return result

if __name__ == "__main__":
    try:
        result = list_versions()
        print(json.dumps(result, indent=2))
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        print(json.dumps(error_result, indent=2))