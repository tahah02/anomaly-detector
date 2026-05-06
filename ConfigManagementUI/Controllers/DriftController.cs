using Microsoft.AspNetCore.Mvc;
using ConfigManagementUI.Models.DbModels;
using ConfigManagementUI.Models.ViewModels;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

namespace ConfigManagementUI.Controllers
{
    public class DriftController : Controller
    {
        private readonly ConfigDbContext _context;
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly string _apiBaseUrl;

        public DriftController(ConfigDbContext context, IHttpClientFactory httpClientFactory, IConfiguration configuration)
        {
            _context = context;
            _httpClientFactory = httpClientFactory;
            _apiBaseUrl = configuration["ApiSettings:BaseUrl"] ?? "http://localhost:8000";
        }

        public IActionResult Index()
        {
            var viewModel = new DriftMonitoringViewModel
            {
                CurrentStatus = GetCurrentStatus(),
                History = GetHistoryItems(30)
            };

            return View(viewModel);
        }

        [HttpGet]
        public IActionResult GetStatus()
        {
            var status = GetCurrentStatus();
            return Json(status);
        }

        [HttpPost]
        public async Task<IActionResult> RunCheck()
        {
            try
            {
                var client = _httpClientFactory.CreateClient();
                var response = await client.PostAsync($"{_apiBaseUrl}/api/drift/run", null);

                if (response.IsSuccessStatusCode)
                {
                    var content = await response.Content.ReadAsStringAsync();
                    return Json(new { success = true, message = "Drift check completed successfully", data = content });
                }
                else
                {
                    return Json(new { success = false, message = "Failed to run drift check" });
                }
            }
            catch (Exception ex)
            {
                return Json(new { success = false, message = ex.Message });
            }
        }

        [HttpGet]
        public IActionResult GetHistory(int limit = 30)
        {
            var history = GetHistoryItems(limit);
            return Json(history);
        }

        private DriftStatusViewModel GetCurrentStatus()
        {
            var latestResult = _context.DriftMonitoringResults
                .Where(d => d.DriftType == "full_monitoring")
                .OrderByDescending(d => d.CheckDate)
                .FirstOrDefault();

            if (latestResult == null)
            {
                return new DriftStatusViewModel
                {
                    OverallStatus = "NO_DATA",
                    CheckDate = DateTime.Now,
                    DriftDetected = false,
                    FeaturesAffected = new List<string>(),
                    Recommendation = "No drift monitoring data available",
                    StatusClass = "secondary",
                    StatusIcon = "info-circle"
                };
            }

            var featuresAffected = new List<string>();
            if (!string.IsNullOrEmpty(latestResult.FeaturesAffected))
            {
                try
                {
                    featuresAffected = JsonSerializer.Deserialize<List<string>>(latestResult.FeaturesAffected);
                }
                catch
                {
                    featuresAffected = new List<string>();
                }
            }

            var statusClass = latestResult.OverallStatus switch
            {
                "CRITICAL" => "danger",
                "WARNING" => "warning",
                "CAUTION" => "info",
                "HEALTHY" => "success",
                _ => "secondary"
            };

            var statusIcon = latestResult.OverallStatus switch
            {
                "CRITICAL" => "exclamation-triangle",
                "WARNING" => "exclamation-circle",
                "CAUTION" => "info-circle",
                "HEALTHY" => "check-circle",
                _ => "question-circle"
            };

            return new DriftStatusViewModel
            {
                Id = latestResult.Id,
                CheckDate = latestResult.CheckDate,
                OverallStatus = latestResult.OverallStatus,
                DriftDetected = latestResult.DriftDetected,
                DriftScore = latestResult.DriftScore,
                FeaturesAffected = featuresAffected,
                Recommendation = latestResult.Recommendation,
                StatusClass = statusClass,
                StatusIcon = statusIcon
            };
        }

        private List<DriftHistoryItemViewModel> GetHistoryItems(int limit)
        {
            var results = _context.DriftMonitoringResults
                .Where(d => d.DriftType == "full_monitoring")
                .OrderByDescending(d => d.CheckDate)
                .Take(limit)
                .ToList();

            return results.Select(r =>
            {
                var featuresCount = 0;
                if (!string.IsNullOrEmpty(r.FeaturesAffected))
                {
                    try
                    {
                        var features = JsonSerializer.Deserialize<List<string>>(r.FeaturesAffected);
                        featuresCount = features?.Count ?? 0;
                    }
                    catch
                    {
                        featuresCount = 0;
                    }
                }

                var statusClass = r.OverallStatus switch
                {
                    "CRITICAL" => "danger",
                    "WARNING" => "warning",
                    "CAUTION" => "info",
                    "HEALTHY" => "success",
                    _ => "secondary"
                };

                return new DriftHistoryItemViewModel
                {
                    Id = r.Id,
                    CheckDate = r.CheckDate,
                    OverallStatus = r.OverallStatus,
                    DriftDetected = r.DriftDetected,
                    DriftScore = r.DriftScore,
                    FeaturesAffectedCount = featuresCount,
                    StatusClass = statusClass
                };
            }).ToList();
        }
    }
}
