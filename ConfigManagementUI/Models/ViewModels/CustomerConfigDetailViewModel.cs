namespace ConfigManagementUI.Models.ViewModels
{
    public class CustomerConfigDetailViewModel
    {
        public string? CustomerID { get; set; }
        public string? AccountNo { get; set; }
        public string? TransferType { get; set; }
        
        public bool VelocityCheck10Min { get; set; }
        public bool VelocityCheck1Hour { get; set; }
        public bool MonthlySpendingCheck { get; set; }
        public bool NewBeneficiaryCheck { get; set; }
        public bool IsolationForestCheck { get; set; }
        public bool AutoencoderCheck { get; set; }
        
        public bool IsNewConfig { get; set; }
    }
}
