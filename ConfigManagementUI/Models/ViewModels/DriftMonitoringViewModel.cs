using System;
using System.Collections.Generic;

namespace ConfigManagementUI.Models.ViewModels
{
    public class DriftMonitoringViewModel
    {
        public DriftStatusViewModel CurrentStatus { get; set; } = new DriftStatusViewModel();
        public List<DriftHistoryItemViewModel> History { get; set; } = new List<DriftHistoryItemViewModel>();
    }

    public class DriftStatusViewModel
    {
        public int Id { get; set; }
        public DateTime CheckDate { get; set; }
        public string OverallStatus { get; set; } = string.Empty;
        public bool DriftDetected { get; set; }
        public double? DriftScore { get; set; }
        public List<string> FeaturesAffected { get; set; } = new List<string>();
        public string Recommendation { get; set; } = string.Empty;
        public string StatusClass { get; set; } = string.Empty;
        public string StatusIcon { get; set; } = string.Empty;
    }

    public class DriftHistoryItemViewModel
    {
        public int Id { get; set; }
        public DateTime CheckDate { get; set; }
        public string OverallStatus { get; set; } = string.Empty;
        public bool DriftDetected { get; set; }
        public double? DriftScore { get; set; }
        public int FeaturesAffectedCount { get; set; }
        public string StatusClass { get; set; } = string.Empty;
    }
}
