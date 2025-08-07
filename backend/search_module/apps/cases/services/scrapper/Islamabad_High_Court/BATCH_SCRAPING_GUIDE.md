# 🚀 Batch-Based Scraping System Guide

## 📊 **System Overview**

This system processes case numbers in batches with **5 parallel browser windows** simultaneously:

- **Batch 1**: Cases 1, 2, 3, 4, 5
- **Batch 2**: Cases 6, 7, 8, 9, 10
- **Batch 3**: Cases 11, 12, 13, 14, 15
- And so on...

## 🎯 **Key Features**

### **1. Parallel Processing**
- **5 browser windows** open simultaneously
- **Each window** processes a different case number
- **Thread-safe** progress tracking

### **2. Individual File Saving**
- **Each case** saved to its own file: `case1.json`, `case2.json`, etc.
- **Continuous saving** - no data loss
- **Immediate backup** after each case completion

### **3. Batch-Based Processing**
- **Easy to control** which batch to run
- **Resume capability** from any batch
- **Progress tracking** per batch

### **4. Multiple Output Formats**
```
cases_metadata/Islamabad_High_Court/
├── individual_cases/
│   ├── case1.json          # Individual case files
│   ├── case2.json
│   ├── case3.json
│   └── ...
├── batch_1_results.json    # Combined batch results
├── batch_1_progress.json   # Progress tracking
└── all_batches_1_10.json  # Combined results
```

## 🛠️ **Usage Options**

### **Option 1: Single Batch (Recommended for Testing)**
```python
# In the main file, change the batch number:
run_single_batch(batch_number=1, cases_per_batch=5, max_workers=5)
```

**What it does:**
- Opens 5 browser windows
- Processes cases 1, 2, 3, 4, 5 simultaneously
- Saves each case to individual files
- Creates `batch_1_results.json` with combined results

### **Option 2: Multiple Batches**
```python
# Uncomment this line in the main file:
run_multiple_batches(start_batch=1, end_batch=10, cases_per_batch=5, max_workers=5)
```

**What it does:**
- Runs batches 1-10 sequentially
- Processes cases 1-50 (10 batches × 5 cases)
- Each batch runs independently
- Can resume from any point

### **Option 3: All 1000 Cases**
```python
# For complete scraping:
run_multiple_batches(start_batch=1, end_batch=200, cases_per_batch=5, max_workers=5)
```

**What it does:**
- Runs all 200 batches (1000 cases)
- Estimated time: 8-12 hours
- Each batch is independent and resumable

## 📁 **File Structure**

### **Individual Case Files**
```
cases_metadata/Islamabad_High_Court/individual_cases/
├── case1.json     # Case number 1 results
├── case2.json     # Case number 2 results
├── case3.json     # Case number 3 results
├── case4.json     # Case number 4 results
├── case5.json     # Case number 5 results
└── ...
```

### **Batch Files**
```
cases_metadata/Islamabad_High_Court/
├── batch_1_results.json    # Combined results for batch 1
├── batch_1_progress.json   # Progress tracking for batch 1
├── batch_2_results.json    # Combined results for batch 2
├── batch_2_progress.json   # Progress tracking for batch 2
└── ...
```

### **Combined Results**
```
cases_metadata/Islamabad_High_Court/
├── all_batches_1_10.json   # All batches 1-10 combined
├── all_batches_1_50.json   # All batches 1-50 combined
└── all_batches_1_200.json  # All 1000 cases combined
```

## 🔧 **Configuration Options**

### **Batch Number**
```python
# Change this to run different batches:
batch_number=1    # Cases 1-5
batch_number=2    # Cases 6-10
batch_number=3    # Cases 11-15
# etc.
```

### **Cases Per Batch**
```python
# Change batch size:
cases_per_batch=5    # 5 cases per batch (default)
cases_per_batch=10   # 10 cases per batch
cases_per_batch=3    # 3 cases per batch
```

### **Parallel Workers**
```python
# Change number of parallel browsers:
max_workers=5    # 5 parallel windows (default)
max_workers=3    # 3 parallel windows (slower but safer)
max_workers=7    # 7 parallel windows (faster but riskier)
```

## 📈 **Expected Performance**

### **Single Batch (5 cases)**
- **Duration**: 10-15 minutes
- **Expected Cases**: 2,500+ cases (500 per case number)
- **Risk Level**: Low

### **10 Batches (50 cases)**
- **Duration**: 2-3 hours
- **Expected Cases**: 25,000+ cases
- **Risk Level**: Medium

### **All 200 Batches (1000 cases)**
- **Duration**: 8-12 hours
- **Expected Cases**: 500,000+ cases
- **Risk Level**: High (but resumable)

## 🚨 **Resume Capability**

### **If Interrupted During a Batch**
The system automatically:
1. **Saves progress** after each case
2. **Skips completed cases** on restart
3. **Continues from where it left off**

### **To Resume a Specific Batch**
```python
# Just run the same batch again:
run_single_batch(batch_number=1, cases_per_batch=5, max_workers=5)
# It will skip already completed cases
```

### **To Resume Multiple Batches**
```python
# Start from a specific batch:
run_multiple_batches(start_batch=5, end_batch=10, cases_per_batch=5, max_workers=5)
# This will run batches 5-10, skipping any completed cases
```

## 💡 **Best Practices**

### **1. Start Small**
```python
# Test with batch 1 first:
run_single_batch(batch_number=1, cases_per_batch=5, max_workers=5)
```

### **2. Monitor Progress**
```bash
# Check individual case files:
ls -la cases_metadata/Islamabad_High_Court/individual_cases/

# Check batch progress:
cat cases_metadata/Islamabad_High_Court/batch_1_progress.json
```

### **3. Run During Off-Peak Hours**
- **Night time** is best for large runs
- **Stable internet** connection required
- **No system sleep/hibernate**

### **4. Monitor System Resources**
- **CPU usage** will be high with 5 browsers
- **Memory usage** will increase
- **Disk space** needed for individual files

## 🔍 **Monitoring Commands**

### **Check Individual Case Files**
```bash
ls -la cases_metadata/Islamabad_High_Court/individual_cases/
```

### **Check Batch Progress**
```bash
cat cases_metadata/Islamabad_High_Court/batch_1_progress.json
```

### **Count Total Cases**
```bash
find cases_metadata/Islamabad_High_Court/individual_cases/ -name "*.json" -exec wc -l {} +
```

### **Check File Sizes**
```bash
du -sh cases_metadata/Islamabad_High_Court/individual_cases/
```

## 🎯 **Quick Start Guide**

### **Step 1: Test Single Batch**
```python
# In ihc_selenium_scraper.py, make sure this line is active:
run_single_batch(batch_number=1, cases_per_batch=5, max_workers=5)
```

### **Step 2: Run the Script**
```bash
python apps/cases/services/scrapper/Islamabad_High_Court/ihc_selenium_scraper.py
```

### **Step 3: Monitor Progress**
- Watch the console output
- Check individual case files
- Monitor system resources

### **Step 4: Scale Up**
```python
# For multiple batches:
run_multiple_batches(start_batch=1, end_batch=10, cases_per_batch=5, max_workers=5)
```

## 🚀 **Ready to Scale**

This system is designed to handle **all 1000 case numbers** efficiently:

- **200 batches** of 5 cases each
- **5 parallel browsers** per batch
- **Individual file saving** prevents data loss
- **Resume capability** from any point
- **Progress tracking** for monitoring

**Estimated total time**: 8-12 hours for all 1000 cases
**Expected total cases**: 500,000+ cases
**Storage requirement**: ~2-5 GB for all files

The system is now ready for production use! 🎉 