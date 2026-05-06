namespace ConfigManagementUI.Models.DbModels
{
    public class FeaturesConfig
    {
        public int FeatureID { get; set; }
        public string? FeatureName { get; set; }
        public string? Description { get; set; }
        public bool IsEnabled { get; set; }
        public bool IsActive { get; set; }
        public string? FeatureType { get; set; }
        public string? Version { get; set; }
        public string? RollbackVersion { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime UpdatedAt { get; set; }
        public string? CreatedBy { get; set; }
        public string? UpdatedBy { get; set; }
    }
}
