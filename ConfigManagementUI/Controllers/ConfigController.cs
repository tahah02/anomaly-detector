using ConfigManagementUI.Models.DbModels;
using ConfigManagementUI.Models.ViewModels;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace ConfigManagementUI.Controllers
{
    public class ConfigController : Controller
    {
        private readonly ConfigDbContext _context;
        private readonly ILogger<ConfigController> _logger;

        public ConfigController(ConfigDbContext context, ILogger<ConfigController> logger)
        {
            _context = context;
            _logger = logger;
        }

        public async Task<IActionResult> Index()
        {
            return View();
        }

        public async Task<IActionResult> Features()
        {
            var features = await _context.FeaturesConfig
                .Select(f => new FeatureConfigViewModel
                {
                    FeatureID = f.FeatureID,
                    FeatureName = f.FeatureName,
                    Description = f.Description,
                    IsEnabled = f.IsEnabled,
                    IsActive = f.IsActive,
                    FeatureType = f.FeatureType,
                    Version = f.Version,
                    UpdatedAt = f.UpdatedAt
                })
                .ToListAsync();

            return View(features);
        }

        public async Task<IActionResult> Thresholds()
        {
            var thresholds = await _context.ThresholdConfig
                .Select(t => new ThresholdConfigViewModel
                {
                    ThresholdID = t.ThresholdID,
                    ThresholdName = t.ThresholdName,
                    ThresholdType = t.ThresholdType,
                    ThresholdValue = t.ThresholdValue,
                    MinValue = t.MinValue,
                    MaxValue = t.MaxValue,
                    IsActive = t.IsActive,
                    Description = t.Description,
                    EffectiveFrom = t.EffectiveFrom,
                    EffectiveTo = t.EffectiveTo,
                    ApprovalStatus = t.ApprovalStatus
                })
                .ToListAsync();

            return View(thresholds);
        }

        public async Task<IActionResult> Scheduler()
        {
            var config = await _context.RetrainingConfig.OrderByDescending(x => x.ConfigId).FirstOrDefaultAsync();
            if (config == null)
                return NotFound();

            var viewModel = new RetrainingConfigViewModel
            {
                ConfigId = config.ConfigId,
                Interval = config.Interval,
                IsEnabled = config.IsEnabled,
                LastRun = config.LastRun,
                NextRun = config.NextRun,
                WeeklyJobDay = config.WeeklyJobDay,
                WeeklyJobHour = config.WeeklyJobHour,
                WeeklyJobMinute = config.WeeklyJobMinute,
                MonthlyJobDay = config.MonthlyJobDay,
                MonthlyJobHour = config.MonthlyJobHour,
                MonthlyJobMinute = config.MonthlyJobMinute
            };

            return View(viewModel);
        }

        public async Task<IActionResult> ModelVersions()
        {
            var models = await _context.ModelVersionConfig
                .OrderByDescending(m => m.CreatedAt)
                .ToListAsync();

            return View(models);
        }

        public async Task<IActionResult> TrainingRuns()
        {
            var runs = await _context.ModelTrainingRuns
                .OrderByDescending(r => r.RunDate)
                .Take(100)
                .ToListAsync();

            return View(runs);
        }

        [HttpPost]
        public async Task<IActionResult> ToggleFeature(int id)
        {
            var feature = await _context.FeaturesConfig.FindAsync(id);
            if (feature == null)
                return NotFound();

            feature.IsEnabled = !feature.IsEnabled;
            feature.UpdatedAt = DateTime.Now;
            feature.UpdatedBy = User.Identity?.Name ?? "System";

            await _context.SaveChangesAsync();
            return Ok(new { success = true, isEnabled = feature.IsEnabled });
        }

        [HttpPost]
        public async Task<IActionResult> UpdateFeature(int id, [FromBody] dynamic model)
        {
            var feature = await _context.FeaturesConfig.FindAsync(id);
            if (feature == null)
                return NotFound();

            feature.FeatureType = model.featureType ?? feature.FeatureType;
            feature.Version = model.version ?? feature.Version;
            feature.Description = model.description ?? feature.Description;
            feature.IsActive = model.isActive;
            feature.UpdatedAt = DateTime.Now;
            feature.UpdatedBy = User.Identity?.Name ?? "System";

            await _context.SaveChangesAsync();
            return Ok(new { success = true });
        }

        [HttpPost]
        public async Task<IActionResult> UpdateThreshold(int id, double thresholdValue, double? minValue, double? maxValue, string? approvalStatus)
        {
            var threshold = await _context.ThresholdConfig.FindAsync(id);
            if (threshold == null)
                return NotFound();

            if (thresholdValue < (minValue ?? 0) || thresholdValue > (maxValue ?? double.MaxValue))
                return BadRequest("Value out of range");

            threshold.PreviousValue = threshold.ThresholdValue;
            threshold.ThresholdValue = thresholdValue;
            
            if (minValue.HasValue)
                threshold.MinValue = minValue;
            
            if (maxValue.HasValue)
                threshold.MaxValue = maxValue;
            
            if (!string.IsNullOrEmpty(approvalStatus))
                threshold.ApprovalStatus = approvalStatus;
            
            threshold.UpdatedAt = DateTime.Now;
            threshold.UpdatedBy = User.Identity?.Name ?? "System";

            await _context.SaveChangesAsync();
            return Ok(new { success = true });
        }

        [HttpPost]
        public async Task<IActionResult> UpdateScheduler(RetrainingConfigViewModel model, bool IsEnabled = false)
        {
            var config = await _context.RetrainingConfig.FindAsync(model.ConfigId);
            if (config == null)
                return NotFound();

            // Log incoming values
            Console.WriteLine($"Received - IsEnabled: {IsEnabled}, Interval: {model.Interval}, Day: {model.WeeklyJobDay}, Hour: {model.WeeklyJobHour}, Minute: {model.WeeklyJobMinute}");

            config.IsEnabled = IsEnabled;
            config.Interval = model.Interval;
            config.WeeklyJobDay = model.WeeklyJobDay;
            config.WeeklyJobHour = model.WeeklyJobHour;
            config.WeeklyJobMinute = model.WeeklyJobMinute;
            config.MonthlyJobDay = model.MonthlyJobDay;
            config.MonthlyJobHour = model.MonthlyJobHour;
            config.MonthlyJobMinute = model.MonthlyJobMinute;
            config.UpdatedAt = DateTime.Now;

            // Calculate Next Run time for Weekly Job
            if (config.IsEnabled && config.WeeklyJobDay.HasValue && config.WeeklyJobHour.HasValue && config.WeeklyJobMinute.HasValue)
            {
                var now = DateTime.Now;
                var targetDayOfWeek = (DayOfWeek)config.WeeklyJobDay.Value;
                var currentDayOfWeek = now.DayOfWeek;
                
                Console.WriteLine($"Calculating NextRun - Current: {now}, Target Day: {targetDayOfWeek}");
                
                // Calculate days until target day
                int daysUntilTarget = ((int)targetDayOfWeek - (int)currentDayOfWeek + 7) % 7;
                
                // If it's the same day, check if time has passed
                if (daysUntilTarget == 0)
                {
                    var targetTime = new TimeSpan(config.WeeklyJobHour.Value, config.WeeklyJobMinute.Value, 0);
                    if (now.TimeOfDay >= targetTime)
                    {
                        // Time has passed today, schedule for next week
                        daysUntilTarget = 7;
                    }
                }
                
                // Calculate next run date and time
                var nextRunDate = now.Date.AddDays(daysUntilTarget);
                config.NextRun = new DateTime(
                    nextRunDate.Year, 
                    nextRunDate.Month, 
                    nextRunDate.Day, 
                    config.WeeklyJobHour.Value, 
                    config.WeeklyJobMinute.Value, 
                    0
                );
                
                Console.WriteLine($"NextRun calculated: {config.NextRun}");
            }
            else
            {
                config.NextRun = null;
                Console.WriteLine($"NextRun set to null - IsEnabled: {config.IsEnabled}, HasDay: {config.WeeklyJobDay.HasValue}, HasHour: {config.WeeklyJobHour.HasValue}, HasMinute: {config.WeeklyJobMinute.HasValue}");
            }

            await _context.SaveChangesAsync();
            Console.WriteLine("Changes saved to database");
            
            TempData["SuccessMessage"] = "Configuration saved successfully!";
            return RedirectToAction("Scheduler");
        }

        public IActionResult CustomerConfigs()
        {
            return View();
        }

        [HttpPost]
        public async Task<IActionResult> SearchCustomer(string customerId)
        {
            var configs = await _context.CustomerAccountTransferTypeConfig
                .Where(c => c.CustomerID == customerId)
                .GroupBy(c => new { c.CustomerID, c.AccountNo, c.TransferType })
                .Select(g => new CustomerConfigListViewModel
                {
                    CustomerID = g.Key.CustomerID,
                    AccountNo = g.Key.AccountNo,
                    TransferType = g.Key.TransferType,
                    EnabledChecksCount = g.Count(x => x.IsEnabled == true),
                    HasConfig = true
                })
                .ToListAsync();

            ViewBag.SearchType = "Customer";
            ViewBag.SearchValue = customerId;
            return View("CustomerConfigResults", configs);
        }

        [HttpPost]
        public async Task<IActionResult> SearchAccount(string accountNo)
        {
            var configs = await _context.CustomerAccountTransferTypeConfig
                .Where(c => c.AccountNo == accountNo)
                .GroupBy(c => new { c.CustomerID, c.AccountNo, c.TransferType })
                .Select(g => new CustomerConfigListViewModel
                {
                    CustomerID = g.Key.CustomerID,
                    AccountNo = g.Key.AccountNo,
                    TransferType = g.Key.TransferType,
                    EnabledChecksCount = g.Count(x => x.IsEnabled == true),
                    HasConfig = true
                })
                .ToListAsync();

            ViewBag.SearchType = "Account";
            ViewBag.SearchValue = accountNo;
            return View("CustomerConfigResults", configs);
        }

        public async Task<IActionResult> CustomerConfigDetail(string customerId, string accountNo, string transferType)
        {
            var configs = await _context.CustomerAccountTransferTypeConfig
                .Where(c => c.CustomerID == customerId && c.AccountNo == accountNo && c.TransferType == transferType)
                .ToListAsync();

            var viewModel = new CustomerConfigDetailViewModel
            {
                CustomerID = customerId,
                AccountNo = accountNo,
                TransferType = transferType,
                IsNewConfig = !configs.Any()
            };

            foreach (var config in configs)
            {
                switch (config.ParameterName)
                {
                    case "velocity_check_10min":
                        viewModel.VelocityCheck10Min = config.IsEnabled ?? false;
                        break;
                    case "velocity_check_1hour":
                        viewModel.VelocityCheck1Hour = config.IsEnabled ?? false;
                        break;
                    case "monthly_spending_check":
                        viewModel.MonthlySpendingCheck = config.IsEnabled ?? false;
                        break;
                    case "new_beneficiary_check":
                        viewModel.NewBeneficiaryCheck = config.IsEnabled ?? false;
                        break;
                    case "isolation_forest_check":
                        viewModel.IsolationForestCheck = config.IsEnabled ?? false;
                        break;
                    case "autoencoder_check":
                        viewModel.AutoencoderCheck = config.IsEnabled ?? false;
                        break;
                }
            }

            return View(viewModel);
        }

        public IActionResult CreateCustomerConfig(string customerId, string? accountNo)
        {
            var viewModel = new CustomerConfigDetailViewModel
            {
                CustomerID = customerId,
                AccountNo = accountNo,
                IsNewConfig = true,
                VelocityCheck10Min = true,
                VelocityCheck1Hour = true,
                MonthlySpendingCheck = true,
                NewBeneficiaryCheck = true,
                IsolationForestCheck = true,
                AutoencoderCheck = true
            };

            return View("CustomerConfigDetail", viewModel);
        }

        [HttpPost]
        public async Task<IActionResult> SaveCustomerConfig(CustomerConfigDetailViewModel model, bool VelocityCheck10Min = false, bool VelocityCheck1Hour = false, bool MonthlySpendingCheck = false, bool NewBeneficiaryCheck = false, bool IsolationForestCheck = false, bool AutoencoderCheck = false)
        {
            var existing = _context.CustomerAccountTransferTypeConfig
                .Where(c => c.CustomerID == model.CustomerID && c.AccountNo == model.AccountNo && c.TransferType == model.TransferType);

            _context.CustomerAccountTransferTypeConfig.RemoveRange(existing);

            var now = DateTime.Now;
            var configs = new List<CustomerAccountTransferTypeConfig>
            {
                new() { CustomerID = model.CustomerID, AccountNo = model.AccountNo, TransferType = model.TransferType, ParameterName = "velocity_check_10min", IsEnabled = VelocityCheck10Min, CreatedAt = now, UpdatedAt = now },
                new() { CustomerID = model.CustomerID, AccountNo = model.AccountNo, TransferType = model.TransferType, ParameterName = "velocity_check_1hour", IsEnabled = VelocityCheck1Hour, CreatedAt = now, UpdatedAt = now },
                new() { CustomerID = model.CustomerID, AccountNo = model.AccountNo, TransferType = model.TransferType, ParameterName = "monthly_spending_check", IsEnabled = MonthlySpendingCheck, CreatedAt = now, UpdatedAt = now },
                new() { CustomerID = model.CustomerID, AccountNo = model.AccountNo, TransferType = model.TransferType, ParameterName = "new_beneficiary_check", IsEnabled = NewBeneficiaryCheck, CreatedAt = now, UpdatedAt = now },
                new() { CustomerID = model.CustomerID, AccountNo = model.AccountNo, TransferType = model.TransferType, ParameterName = "isolation_forest_check", IsEnabled = IsolationForestCheck, CreatedAt = now, UpdatedAt = now },
                new() { CustomerID = model.CustomerID, AccountNo = model.AccountNo, TransferType = model.TransferType, ParameterName = "autoencoder_check", IsEnabled = AutoencoderCheck, CreatedAt = now, UpdatedAt = now }
            };

            _context.CustomerAccountTransferTypeConfig.AddRange(configs);
            await _context.SaveChangesAsync();

            TempData["SuccessMessage"] = "Configuration saved successfully!";
            TempData["SavedCustomerId"] = model.CustomerID;
            return RedirectToAction("CustomerConfigs");
        }

        [HttpPost]
        public async Task<IActionResult> DeleteCustomerConfig(string customerId, string accountNo, string transferType)
        {
            var configs = _context.CustomerAccountTransferTypeConfig
                .Where(c => c.CustomerID == customerId && c.AccountNo == accountNo && c.TransferType == transferType);

            _context.CustomerAccountTransferTypeConfig.RemoveRange(configs);
            await _context.SaveChangesAsync();

            TempData["SuccessMessage"] = "Configuration deleted successfully!";
            return RedirectToAction("CustomerConfigs");
        }
    }
}
