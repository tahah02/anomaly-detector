using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace ConfigManagementUI.Models.DbModels
{
    [Table("DriftMonitoringResults")]
    public class DriftMonitoringResult
    {
        [Key]
        public int Id { get; set; }

        [Required]
        public DateTime CheckDate { get; set; }

        [Required]
        [StringLength(50)]
        public string DriftType { get; set; } = string.Empty;

        [Required]
        public bool DriftDetected { get; set; }

        public double? DriftScore { get; set; }

        public string? FeaturesAffected { get; set; }

        [StringLength(20)]
        public string? OverallStatus { get; set; }

        [StringLength(500)]
        public string? Recommendation { get; set; }

        public string? ResultsJson { get; set; }

        public DateTime CreatedAt { get; set; }
    }
}
