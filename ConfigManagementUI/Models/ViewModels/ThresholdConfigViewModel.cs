namespace ConfigManagementUI.Models.ViewModels
{
    public class ThresholdConfigViewModel
    {
        public int ThresholdID { get; set; }
        public string? ThresholdName { get; set; }
        public string? ThresholdType { get; set; }
        public double ThresholdValue { get; set; }
        public double? MinValue { get; set; }
        public double? MaxValue { get; set; }
        public bool IsActive { get; set; }
        public string? Description { get; set; }
        public DateTime? EffectiveFrom { get; set; }
        public DateTime? EffectiveTo { get; set; }
        public string? ApprovalStatus { get; set; }
        public string ValidationStatus => IsOutOfRange() ? "OUT_OF_RANGE" : "VALID";
        
        private bool IsOutOfRange()
        {
            return ThresholdValue < (MinValue ?? 0) || ThresholdValue > (MaxValue ?? double.MaxValue);
        }
    }
}
