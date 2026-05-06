namespace ConfigManagementUI.Models.DbModels
{
    public class ModelTrainingRuns
    {
        public int RunId { get; set; }
        public DateTime RunDate { get; set; }
        public string? ModelVersion { get; set; }
        public string? Status { get; set; }
        public int DataSize { get; set; }
        public string? Metrics { get; set; }
    }
}
