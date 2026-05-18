import json
import sys
import os

def get_mlflow_runs():
    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        # Set tracking URI to local mlruns directory
        mlflow_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mlruns")
        mlflow.set_tracking_uri(f"file:///{mlflow_dir}")

        client = MlflowClient()

        # Get all experiments (not just specific names)
        all_experiments = client.search_experiments()
        
        experiments = []
        for exp in all_experiments:
            # Skip deleted experiments
            if exp.lifecycle_stage != "deleted":
                experiments.append(exp.experiment_id)

        if not experiments:
            return {
                "success": True,
                "total_runs": 0,
                "runs": [],
                "message": "No MLFlow experiments found. Run training first."
            }

        all_runs = []
        for exp_id in experiments:
            runs = client.search_runs(
                experiment_ids=[exp_id],
                order_by=["start_time DESC"],
                max_results=50
            )
            for run in runs:
                run_data = {
                    "run_id": run.info.run_id[:8],
                    "run_name": run.data.tags.get("mlflow.runName", "unknown"),
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "end_time": run.info.end_time,
                    "duration_seconds": round((run.info.end_time - run.info.start_time) / 1000, 1) if run.info.end_time else None,
                    "model_type": run.data.tags.get("model_type", run.data.tags.get("pipeline_status", "pipeline")),
                    "pipeline_status": run.data.tags.get("pipeline_status", None),
                    "trained_at": run.data.tags.get("trained_at", None),
                    "model_version": run.data.tags.get("model_version", None),
                    "params": dict(run.data.params),
                    "metrics": {k: round(v, 6) for k, v in run.data.metrics.items()}
                }
                all_runs.append(run_data)

        all_runs.sort(key=lambda x: x["start_time"] or 0, reverse=True)

        for run in all_runs:
            if run["start_time"]:
                from datetime import datetime, timezone
                dt = datetime.fromtimestamp(run["start_time"] / 1000, tz=timezone.utc)
                run["start_time"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            if run["end_time"]:
                from datetime import datetime, timezone
                dt = datetime.fromtimestamp(run["end_time"] / 1000, tz=timezone.utc)
                run["end_time"] = dt.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "success": True,
            "total_runs": len(all_runs),
            "runs": all_runs
        }

    except ImportError:
        return {
            "success": False,
            "error": "MLFlow not installed. Run: pip install mlflow",
            "runs": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "runs": []
        }


if __name__ == "__main__":
    try:
        result = get_mlflow_runs()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e), "runs": []}))
