# 🌲 **PINECONE INTEGRATION SETUP GUIDE**

## **📋 PREREQUISITES**

### **1. Pinecone Account**
- Sign up at [pinecone.io](https://pinecone.io)
- Get your **API Key** from the dashboard
- Note your **Environment** (usually `gcp-starter` for free tier)

### **2. Python Environment**
- Python 3.8+ installed
- Django project running
- Required packages installed (see below)

---

## **🔧 INSTALLATION STEPS**

### **Step 1: Install Pinecone Client**
```bash
pip install pinecone-client
```

### **Step 2: Set Environment Variables**
```bash
# Set your Pinecone API key
export PINECONE_API_KEY="your-api-key-here"

# For Windows PowerShell:
$env:PINECONE_API_KEY="your-api-key-here"

# For Windows Command Prompt:
set PINECONE_API_KEY=your-api-key-here
```

### **Step 3: Test Integration**
```bash
python test_pinecone_integration.py
```

---

## **🚀 BUILDING YOUR FIRST INDEX**

### **Step 1: Build Pinecone Index**
```bash
# Build index with your real data
python manage.py build_pinecone_index --force

# Or with custom API key
python manage.py build_pinecone_index --force --api-key "your-key"
```

### **Step 2: Verify Index Creation**
```bash
# Check index statistics
python manage.py shell
```
```python
from search_indexing.services.pinecone_indexing import PineconeIndexingService
service = PineconeIndexingService()
stats = service.get_index_stats()
print(stats)
```

---

## **🔍 TESTING SEARCH FUNCTIONALITY**

### **Basic Search Test**
```python
from search_indexing.services.pinecone_indexing import PineconeIndexingService

# Initialize service
service = PineconeIndexingService()

# Test search
results = service.search("court appeal", top_k=10)
print(f"Found {len(results)} results")

for result in results[:3]:
    print(f"Score: {result['similarity']:.3f}")
    print(f"Case: {result['case_number']}")
    print(f"Title: {result['case_title']}")
    print("---")
```

### **Search with Filters**
```python
# Search for cases in specific court
results = service.search("appeal", filters={'court': 'IHC'}, top_k=5)

# Search for cases by specific judge
results = service.search("petition", filters={'judge': 'Babar Sattar'}, top_k=5)

# Search for pending cases
results = service.search("civil", filters={'status': 'Pending'}, top_k=5)
```

---

## **🔧 HYBRID SEARCH WITH PINECONE**

### **Using Hybrid Service**
```python
from search_indexing.services.hybrid_indexing import HybridIndexingService

# Initialize with Pinecone
hybrid_service = HybridIndexingService(use_pinecone=True)

# Perform hybrid search
results = hybrid_service.hybrid_search("court appeal justice", top_k=10)

# Search with filters
results = hybrid_service.hybrid_search(
    "petition", 
    filters={'court': 'IHC', 'status': 'Pending'}, 
    top_k=10
)
```

---

## **📊 MONITORING & STATISTICS**

### **Index Statistics**
```python
from search_indexing.services.pinecone_indexing import PineconeIndexingService

service = PineconeIndexingService()
stats = service.get_index_stats()

print(f"Index Name: {stats['index_name']}")
print(f"Total Vectors: {stats['total_vector_count']}")
print(f"Dimension: {stats['dimension']}")
print(f"Metric: {stats['metric']}")
print(f"Status: {stats['status']}")
```

### **Pinecone Dashboard**
- Visit [app.pinecone.io](https://app.pinecone.io)
- Check your index statistics
- Monitor query usage (free tier: 10K queries/month)

---

## **⚠️ FREE TIER LIMITATIONS**

### **Current Limits**
- **1 Project** (perfect for your use case)
- **1 Index** (exactly what you need)
- **100,000 vectors** (you have 545 - plenty of room!)
- **10,000 queries/month** (good for testing/development)

### **Monitoring Usage**
```python
# Check your current usage
import pinecone
pinecone.init(api_key="your-key", environment="gcp-starter")

# List your indexes
indexes = pinecone.list_indexes()
print(f"Your indexes: {indexes}")

# Get index description
index_description = pinecone.describe_index("legal-cases-index")
print(f"Vector count: {index_description.total_vector_count}")
```

---

## **🔧 TROUBLESHOOTING**

### **Common Issues**

#### **1. API Key Not Found**
```bash
# Error: Pinecone API key not found
# Solution: Set environment variable
export PINECONE_API_KEY="your-api-key-here"
```

#### **2. Index Already Exists**
```bash
# Error: Index already exists
# Solution: Use --force flag
python manage.py build_pinecone_index --force
```

#### **3. Network Issues**
```python
# Error: Connection timeout
# Solution: Check internet connection and try again
# Pinecone requires internet access
```

#### **4. Query Limit Reached**
```python
# Error: Query limit exceeded
# Solution: Monitor usage in Pinecone dashboard
# Free tier: 10,000 queries/month
```

---

## **📈 PERFORMANCE COMPARISON**

### **FAISS vs Pinecone**

| Feature | FAISS | Pinecone |
|---------|-------|----------|
| **Speed** | ⚡ Very Fast | 🚀 Fast |
| **Memory** | 💾 High | 💾 Low |
| **Scaling** | 📈 Limited | 📈 Unlimited |
| **Cost** | 💰 Free | 💰 Free (tier) |
| **Updates** | 🔄 Manual | 🔄 Real-time |
| **Filtering** | ❌ Basic | ✅ Advanced |

### **Your Data Scale**
- **545 vectors** (well within 100K limit)
- **384 dimensions** (supported)
- **Occasional rebuilds** (perfect for free tier)

---

## **🎯 RECOMMENDATIONS**

### **For Your Project**
1. **✅ Use Pinecone Free Tier** - Perfect for your scale
2. **✅ Monitor Query Usage** - Stay under 10K/month
3. **✅ Use Metadata Filtering** - Great for legal cases
4. **✅ Keep FAISS as Backup** - For offline scenarios

### **Production Considerations**
1. **Upgrade to Paid** when you reach 10K+ vectors
2. **Implement Caching** for repeated queries
3. **Add Error Handling** for network issues
4. **Monitor Performance** vs FAISS

---

## **🔗 USEFUL LINKS**

- [Pinecone Documentation](https://docs.pinecone.io/)
- [Pinecone Dashboard](https://app.pinecone.io/)
- [Free Tier Limits](https://www.pinecone.io/pricing/)
- [API Reference](https://docs.pinecone.io/docs/python-client)

---

## **✅ SUCCESS CHECKLIST**

- [ ] Pinecone account created
- [ ] API key obtained
- [ ] Environment variable set
- [ ] Client installed (`pip install pinecone-client`)
- [ ] Integration test passed (`python test_pinecone_integration.py`)
- [ ] Index built (`python manage.py build_pinecone_index --force`)
- [ ] Search functionality tested
- [ ] Hybrid search working
- [ ] Dashboard monitoring set up

**🎉 Congratulations! Your Pinecone integration is ready!**
