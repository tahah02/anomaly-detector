namespace ConfigManagementUI.Models.DbModels
{
    public class ThresholdConfig
    {
        public int ThresholdID { get; set; }
        public string? ThresholdName { get; set; }
        public string? ThresholdType { get; set; }
        public double ThresholdValue { get; set; }
        public double? MinValue { get; set; }
        public double? MaxValue { get; set; }
        public double? PreviousValue { get; set; }
        public string? Description { get; set; }
        public bool IsActive { get; set; }
        public DateTime? EffectiveFrom { get; set; }
        public DateTime? EffectiveTo { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime UpdatedAt { get; set; }
        public string? CreatedBy { get; set; }
        public string? UpdatedBy { get; set; }
        public string? ApprovalStatus { get; set; }
        public string? ApprovedBy { get; set; }
        public string? Rationale { get; set; }
        public string? ImpactAnalysis { get; set; }
    }
}
