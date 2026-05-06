namespace ConfigManagementUI.Models.DbModels
{
    public class CustomerAccountTransferTypeConfig
    {
        public int ConfigID { get; set; }
        public string? CustomerID { get; set; }
        public string? AccountNo { get; set; }
        public string? TransferType { get; set; }
        public string? ParameterName { get; set; }
        public string? ParameterValue { get; set; }
        public bool? IsEnabled { get; set; }
        public bool? IsActive { get; set; }
        public string? DataType { get; set; }
        public double? MinValue { get; set; }
        public double? MaxValue { get; set; }
        public string? Description { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime UpdatedAt { get; set; }
        public string? CreatedBy { get; set; }
        public string? UpdatedBy { get; set; }
    }
}
