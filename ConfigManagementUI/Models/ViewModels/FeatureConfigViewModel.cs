namespace ConfigManagementUI.Models.ViewModels
{
    public class FeatureConfigViewModel
    {
        public int FeatureID { get; set; }
        public string? FeatureName { get; set; }
        public string? Description { get; set; }
        public bool IsEnabled { get; set; }
        public bool IsActive { get; set; }
        public string? FeatureType { get; set; }
        public string? Version { get; set; }
        public string Status => IsActive && IsEnabled ? "ACTIVE" : IsActive ? "DISABLED" : "INACTIVE";
        public DateTime UpdatedAt { get; set; }
    }
}
