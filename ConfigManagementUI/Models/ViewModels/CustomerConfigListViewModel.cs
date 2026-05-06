namespace ConfigManagementUI.Models.ViewModels
{
    public class CustomerConfigListViewModel
    {
        public string? CustomerID { get; set; }
        public string? AccountNo { get; set; }
        public string? TransferType { get; set; }
        public int EnabledChecksCount { get; set; }
        public bool HasConfig { get; set; }
    }
}
