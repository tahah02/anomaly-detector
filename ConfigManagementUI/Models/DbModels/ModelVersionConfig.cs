namespace ConfigManagementUI.Models.DbModels
{
    public class ModelVersionConfig
    {
        public int ModelVersionID { get; set; }
        public string? ModelName { get; set; }
        public string? VersionNumber { get; set; }
        public string? ModelPath { get; set; }
        public string? ScalerPath { get; set; }
        public string? ThresholdPath { get; set; }
        public bool IsActive { get; set; }
        public double? Accuracy { get; set; }
        public double? Precision { get; set; }
        public double? Recall { get; set; }
        public double? F1Score { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime? DeployedAt { get; set; }
        public DateTime? RetiredAt { get; set; }
        public string? CreatedBy { get; set; }
        public string? DeployedBy { get; set; }
        public long TrainingDataSize { get; set; }
        public long ModelSize { get; set; }
        public string? Notes { get; set; }
    }
}
