# 🏗️ ConfigManagementUI - Simple Architecture Guide

Easy explanation of how the Config Management UI works.

---

## 🎯 What is it?

A **web dashboard** where you can:
- Change threshold values (like autoencoder_threshold)
- Turn scheduler ON/OFF
- Manage customer rules
- View model versions

**Built with:** ASP.NET Core MVC (C# web framework)

---

## 📊 Architecture Pattern

**Question:** Is it using Repository Pattern?  
**Answer:** ❌ **NO** - Using **Direct DbContext** pattern

**What does this mean?**
- Controller talks directly to database
- No middle layer (repository)
- Simpler but less flexible

**Why this approach?**
- ✅ Faster to build
- ✅ Less code to maintain
- ✅ Good enough for this project size

---

## 🎨 MVC = Model-View-Controller

Think of it like a restaurant:

```
User (Customer) 
    ↓
View (Menu) - What you see
    ↓
Controller (Waiter) - Takes your order
    ↓
Model (Kitchen) - Prepares food (data)
    ↓
Database (Storage) - Ingredients
```

---

## 📦 Three Main Parts

### **1. Models (M) - The Data**

**Two types:**

#### **Database Models** (`DbModels/`)
- Represent actual database tables
- Example: `ThresholdConfig.cs` = ThresholdConfig table

```csharp
public class ThresholdConfig
{
    public int ThresholdID { get; set; }
    public string ThresholdName { get; set; }
    public double ThresholdValue { get; set; }
    public bool IsActive { get; set; }  // ON/OFF switch
}
```

#### **View Models** (`ViewModels/`)
- Simplified data for UI
- Only fields user needs to see

```csharp
public class ThresholdConfigViewModel
{
    public int ThresholdID { get; set; }
    public string ThresholdName { get; set; }
    public double ThresholdValue { get; set; }
    public bool IsActive { get; set; }
    // No audit fields like CreatedAt, UpdatedBy
}
```

**Why two types?**
- Database has extra fields (audit, timestamps)
- UI doesn't need all that
- Keeps views clean

---

### **2. Views (V) - The UI**

**What:** HTML pages with C# code (Razor syntax)  
**Extension:** `.cshtml` files

**Example:** `Thresholds.cshtml`
```html
@model List<ThresholdConfigViewModel>

<table>
    @foreach (var threshold in Model)
    {
        <tr>
            <td>@threshold.ThresholdName</td>
            <td>
                <input type="number" value="@threshold.ThresholdValue" />
            </td>
            <td>
                <input type="checkbox" @(threshold.IsActive ? "checked" : "") />
            </td>
            <td>
                <button onclick="save(@threshold.ThresholdID)">Save</button>
            </td>
        </tr>
    }
</table>
```

**Key Features:**
- `@model` = Data type coming from controller
- `@foreach` = Loop through data
- `@threshold.Property` = Display value
- Mix HTML + C# code

---

### **3. Controllers (C) - The Logic**

**What:** Handles user requests and responses  
**File:** `ConfigController.cs`

**Structure:**
```csharp
public class ConfigController : Controller
{
    private readonly ConfigDbContext _context;  // Database connection
    
    // Constructor - gets database connection
    public ConfigController(ConfigDbContext context)
    {
        _context = context;
    }
    
    // Action methods handle requests...
}
```

**Key Point:** Controller talks **directly** to database (no repository layer)

---

## 🔄 How It Works - Simple Flow

### **Example: Viewing Thresholds**

```
1. User opens browser → http://localhost:5202/Config/Thresholds

2. ASP.NET Core routes request to ConfigController

3. Controller method runs:
   public async Task<IActionResult> Thresholds()
   {
       // Get data from database
       var thresholds = await _context.ThresholdConfig.ToListAsync();
       
       // Send to view
       return View(thresholds);
   }

4. Razor engine processes Thresholds.cshtml
   - Loops through data
   - Generates HTML

5. Browser displays the page
```

---

### **Example: Saving Changes**

```
1. User changes threshold value → clicks Save

2. JavaScript sends POST request

3. Controller receives request:
   [HttpPost]
   public async Task<IActionResult> UpdateThreshold(int id, double value, bool isActive)
   {
       // Find record
       var threshold = await _context.ThresholdConfig.FindAsync(id);
       
       // Update
       threshold.ThresholdValue = value;
       threshold.IsActive = isActive;
       
       // Save to database
       await _context.SaveChangesAsync();
       
       return Ok(new { success = true });
   }

4. JavaScript shows success message
```

---

## 🗄️ Database Connection

**Entity Framework Core** = ORM (Object-Relational Mapping)

**What it does:**
- Converts C# objects ↔ Database tables
- No need to write SQL queries
- Type-safe database access

**Example:**
```csharp
// Instead of SQL:
// SELECT * FROM ThresholdConfig WHERE IsActive = 1

// You write C#:
var active = await _context.ThresholdConfig
    .Where(t => t.IsActive == true)
    .ToListAsync();
```

**DbContext = Database Connection Manager**
```csharp
public class ConfigDbContext : DbContext
{
    public DbSet<ThresholdConfig> ThresholdConfig { get; set; }
    public DbSet<FeaturesConfig> FeaturesConfig { get; set; }
    // Each DbSet = One table
}
```

---

## 🎯 Key Features Built

### **1. Threshold Management**
- View all thresholds in table
- Edit values inline
- Toggle IsActive ON/OFF
- Save changes to database

### **2. Scheduler Control**
- Turn retraining ON/OFF
- Set schedule (weekly/monthly)
- View next run time

### **3. Customer Rules**
- Search by customer ID
- Enable/disable specific checks
- Override global settings

### **4. Model Versions**
- List all versions
- Activate specific version
- Calls Python scripts

---

## 🔧 Technologies Used

### **Backend:**
- **ASP.NET Core 8.0** - Web framework
- **C#** - Programming language
- **Entity Framework Core** - Database ORM
- **SQL Server** - Database

### **Frontend:**
- **Razor** - Template engine (HTML + C#)
- **Bootstrap 5** - CSS framework
- **jQuery** - JavaScript library
- **AJAX** - Async requests

---

## 🚀 Why This Architecture?

### **Advantages:**
✅ **Simple** - Easy to understand  
✅ **Fast** - Quick development  
✅ **Maintainable** - Less code  
✅ **Type-safe** - Compile-time checks  

### **Trade-offs:**
⚠️ **Tight coupling** - Controller depends on database  
⚠️ **Less flexible** - Hard to change data source  

### **Good for:**
✅ Small-medium projects  
✅ Single database  
✅ Simple CRUD operations  

### **Not ideal for:**
❌ Large enterprise apps  
❌ Multiple data sources  
❌ Complex business logic  

---

## 📋 File Structure

```
ConfigManagementUI/
├── Controllers/
│   ├── ConfigController.cs      # Main logic
│   ├── DriftController.cs        # Drift monitoring
│   └── HomeController.cs         # Home page
│
├── Models/
│   ├── DbModels/                 # Database tables
│   │   ├── ThresholdConfig.cs
│   │   ├── RetrainingConfig.cs
│   │   └── ConfigDbContext.cs    # Database connection
│   │
│   └── ViewModels/               # UI data
│       ├── ThresholdConfigViewModel.cs
│       └── RetrainingConfigViewModel.cs
│
├── Views/
│   ├── Config/                   # Config pages
│   │   ├── Thresholds.cshtml
│   │   ├── Scheduler.cshtml
│   │   └── ModelVersions.cshtml
│   │
│   └── Shared/
│       └── _Layout.cshtml        # Master template
│
├── wwwroot/                      # Static files
│   ├── css/
│   ├── js/
│   └── lib/
│
├── appsettings.json              # Configuration
└── Program.cs                    # App startup
```

---

## 🔐 Security

### **Input Validation:**
```csharp
[Required]
[Range(0, 100)]
public double ThresholdValue { get; set; }
```

### **CSRF Protection:**
- Auto-generated tokens in forms
- Prevents cross-site attacks

### **SQL Injection Prevention:**
- Entity Framework parameterizes queries
- No raw SQL strings

---

## 🎓 Key Concepts Summary

### **MVC Pattern:**
- **Model** = Data (database tables)
- **View** = UI (HTML pages)
- **Controller** = Logic (handles requests)

### **Direct DbContext:**
- Controller → DbContext → Database
- No repository layer
- Simpler but less flexible

### **Entity Framework:**
- ORM for database access
- Write C# instead of SQL
- Type-safe queries

### **Razor Views:**
- HTML + C# code
- Server-side rendering
- Strongly-typed models

---

## 💡 Simple Analogy

**Think of the Config UI like a TV Remote:**

- **View (Buttons)** = What you see and press
- **Controller (Circuit)** = Processes your button press
- **Model (TV Settings)** = Actual settings being changed
- **Database (Memory)** = Stores settings permanently

When you press "Volume Up":
1. Button pressed (View)
2. Circuit processes (Controller)
3. Volume setting changes (Model)
4. New volume saved (Database)

Same way:
1. Click "Save" button (View)
2. Controller processes request
3. Threshold value updates (Model)
4. Database saves change

---

## 🎯 Bottom Line

**What:** Web dashboard for configuration management  
**How:** ASP.NET Core MVC with direct database access  
**Why:** Simple, fast, and good enough for this project  

**Not using Repository Pattern because:**
- Project is small-medium size
- Single database
- Simple CRUD operations
- Speed of development matters

**If project grows, can refactor to Repository Pattern later!**

---

**Last Updated:** Phase 2 Complete  
**Pattern:** Direct DbContext (No Repository)  
**Framework:** ASP.NET Core 8.0 MVC
