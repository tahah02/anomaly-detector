import sys
import json
from backend.mlops.model_versioning import get_versioning

def activate_version(version: str):
    versioning = get_versioning()
    
    if version == "base":
        success = versioning.set_current_version("base")
        if success:
            return {
                "success": True,
                "message": f"Base version activated successfully",
                "version": "base"
            }
        else:
            return {"success": False, "error": "Failed to activate base version"}
    
    available_versions = versioning.list_versions()
    if version not in available_versions:
        return {
            "success": False,
            "error": f"Version {version} not found. Available: {', '.join(available_versions)}"
        }
    
    if_metadata = versioning.get_version_metadata(version, "isolation_forest")
    ae_metadata = versioning.get_version_metadata(version, "autoencoder")
    
    if not if_metadata:
        return {"success": False, "error": f"Isolation Forest model not found for version {version}"}
    
    if not ae_metadata:
        return {"success": False, "error": f"Autoencoder model not found for version {version}"}
    
    success = versioning.set_current_version(version)
    
    if success:
        return {
            "success": True,
            "message": f"Version {version} activated successfully",
            "version": version
        }
    else:
        return {"success": False, "error": "Failed to activate version"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        result = {"success": False, "error": "Usage: python activate_model_version.py <version>"}
        print(json.dumps(result, indent=2))
        sys.exit(1)
    
    version = sys.argv[1]
    
    try:
        result = activate_version(version)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        print(json.dumps(error_result, indent=2))
        sys.exit(1)
