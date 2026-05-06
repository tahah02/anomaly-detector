namespace ConfigManagementUI.Models.DbModels
{
    public class RetrainingConfig
    {
        public int ConfigId { get; set; }
        public string? Interval { get; set; }
        public bool IsEnabled { get; set; }
        public DateTime? LastRun { get; set; }
        public DateTime? NextRun { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime UpdatedAt { get; set; }
        public int? WeeklyJobDay { get; set; }
        public int? WeeklyJobHour { get; set; }
        public int? WeeklyJobMinute { get; set; }
        public int? MonthlyJobDay { get; set; }
        public int? MonthlyJobHour { get; set; }
        public int? MonthlyJobMinute { get; set; }
    }
}
