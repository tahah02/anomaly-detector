using Microsoft.EntityFrameworkCore;

namespace ConfigManagementUI.Models.DbModels
{
    public class ConfigDbContext : DbContext
    {
        public ConfigDbContext(DbContextOptions<ConfigDbContext> options) : base(options) { }

        public DbSet<FeaturesConfig> FeaturesConfig { get; set; }
        public DbSet<ThresholdConfig> ThresholdConfig { get; set; }
        public DbSet<RetrainingConfig> RetrainingConfig { get; set; }
        public DbSet<ModelVersionConfig> ModelVersionConfig { get; set; }
        public DbSet<ModelTrainingRuns> ModelTrainingRuns { get; set; }
        public DbSet<CustomerAccountTransferTypeConfig> CustomerAccountTransferTypeConfig { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            modelBuilder.Entity<FeaturesConfig>().ToTable("FeaturesConfig").HasKey(x => x.FeatureID);
            modelBuilder.Entity<ThresholdConfig>().ToTable("ThresholdConfig").HasKey(x => x.ThresholdID);
            modelBuilder.Entity<RetrainingConfig>().ToTable("RetrainingConfig").HasKey(x => x.ConfigId);
            modelBuilder.Entity<ModelVersionConfig>().ToTable("ModelVersionConfig").HasKey(x => x.ModelVersionID);
            modelBuilder.Entity<ModelTrainingRuns>().ToTable("ModelTrainingRuns").HasKey(x => x.RunId);
            modelBuilder.Entity<CustomerAccountTransferTypeConfig>().ToTable("CustomerAccountTransferTypeConfig").HasKey(x => x.ConfigID);
        }
    }
}
