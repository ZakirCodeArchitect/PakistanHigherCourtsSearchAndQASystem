# 🧪 **Complete Testing Guide for Enhanced Legal Chatbot**

## 🌐 **Access Points**

### **Main Chatbot Interface**
- **URL**: `http://127.0.0.1:8000/qa/`
- **Description**: Main chat interface with all new features

### **API Endpoints**
- **QA API**: `http://127.0.0.1:8000/qa/ask/`
- **Sessions**: `http://127.0.0.1:8000/qa/sessions/`
- **History**: `http://127.0.0.1:8000/qa/history/`
- **System Status**: `http://127.0.0.1:8000/qa/status/`
- **Sample Data**: `http://127.0.0.1:8000/qa/data/`

---

## 🎯 **Testing Checklist**

### **1. Basic Chatbot Interface** ✅
**URL**: `http://127.0.0.1:8000/qa/`

**What to Test:**
- [ ] Page loads successfully
- [ ] Chat interface appears
- [ ] Sample questions are clickable
- [ ] Input field works
- [ ] Send button functions

**Expected Result**: Modern chat interface with sample questions

---

### **2. Conversation Memory & Session Management** ✅
**Test Steps:**

#### **Step 1: Create New Session**
```javascript
// Open browser console and run:
fetch('http://127.0.0.1:8000/qa/sessions/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        user_id: 'test_user',
        title: 'Test Session',
        description: 'Testing conversation memory'
    })
}).then(r => r.json()).then(console.log)
```

#### **Step 2: Ask First Question**
- Go to `http://127.0.0.1:8000/qa/`
- Ask: "What is a writ petition?"
- Check if session ID appears in response

#### **Step 3: Ask Follow-up Question**
- Ask: "What are the requirements for filing it?"
- Check if it's detected as follow-up
- Verify context from previous question

**Expected Results:**
- Session ID in responses
- Follow-up detection badge
- Context-aware responses

---

### **3. GPT-4 Integration** ✅
**Test Steps:**

#### **Step 1: Ask Complex Legal Question**
- Question: "Explain the constitutional basis for writ petitions under Article 199"
- Check response quality and structure

#### **Step 2: Check Response Metadata**
- Look for "Model: gpt-4" in response
- Verify confidence scores
- Check token usage

**Expected Results:**
- High-quality legal analysis
- Structured response format
- GPT-4 model indication

---

### **4. Legal Citation Formatting** ✅
**Test Steps:**

#### **Step 1: Ask Case-Specific Question**
- Question: "Tell me about recent writ petition cases"
- Check source citations format

#### **Step 2: Verify Citation Structure**
- Look for proper case citation format
- Check download links
- Verify metadata display

**Expected Results:**
- Proper legal citation format
- Download links for documents
- Court, case number, date information

---

### **5. Advanced Embedding Models** ✅
**Test Steps:**

#### **Step 1: Check System Status**
- Go to: `http://127.0.0.1:8000/qa/status/`
- Look for embedding model information

#### **Step 2: Test Semantic Search**
- Ask: "constitutional remedies"
- Ask: "fundamental rights"
- Compare response relevance

**Expected Results:**
- Advanced embedding model in status
- High relevance scores
- Semantic understanding

---

### **6. Follow-up Query Handling** ✅
**Test Steps:**

#### **Step 1: Start Conversation**
- Ask: "What is bail?"
- Wait for response

#### **Step 2: Ask Follow-up**
- Ask: "How do I apply for it?"
- Check if "Follow-up" badge appears

#### **Step 3: Test Pronoun Resolution**
- Ask: "What documents are needed?"
- Verify it understands "it" refers to bail

**Expected Results:**
- Follow-up detection
- Context-aware responses
- Pronoun resolution

---

### **7. Conversation History** ✅
**Test Steps:**

#### **Step 1: Have Multi-turn Conversation**
- Ask 3-4 related questions
- Check conversation flow

#### **Step 2: Check History API**
```javascript
// Get conversation history
fetch('http://127.0.0.1:8000/qa/history/?session_id=YOUR_SESSION_ID&user_id=test_user')
.then(r => r.json()).then(console.log)
```

**Expected Results:**
- Complete conversation history
- Context retention across turns
- Session statistics

---

## 🔧 **API Testing Commands**

### **Test Session Creation**
```bash
curl -X POST http://127.0.0.1:8000/qa/sessions/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "title": "Test Session"}'
```

### **Test QA with Session**
```bash
curl -X POST http://127.0.0.1:8000/qa/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a writ petition?", "session_id": "YOUR_SESSION_ID", "user_id": "test_user", "use_ai": true}'
```

### **Test Follow-up Query**
```bash
curl -X POST http://127.0.0.1:8000/qa/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the requirements?", "session_id": "YOUR_SESSION_ID", "user_id": "test_user", "use_ai": true}'
```

### **Check System Status**
```bash
curl http://127.0.0.1:8000/qa/status/
```

---

## 🎯 **Specific Test Scenarios**

### **Scenario 1: Legal Research Session**
1. **Start**: "I need help with constitutional law"
2. **Follow-up**: "What are writ petitions?"
3. **Follow-up**: "How do I file one?"
4. **Follow-up**: "What documents do I need?"
5. **Check**: Session history and context retention

### **Scenario 2: Case Analysis**
1. **Start**: "Tell me about recent bail cases"
2. **Follow-up**: "What was the outcome?"
3. **Follow-up**: "Which court decided it?"
4. **Check**: Citation formatting and source links

### **Scenario 3: Procedural Guidance**
1. **Start**: "How do I appeal a court decision?"
2. **Follow-up**: "What's the time limit?"
3. **Follow-up**: "Where do I file it?"
4. **Check**: Practical guidance and next steps

---

## 📊 **What to Look For**

### **✅ Success Indicators**
- **Session Management**: Session IDs in responses
- **Follow-up Detection**: "Follow-up" badges
- **GPT-4 Responses**: High-quality legal analysis
- **Citation Format**: Proper legal citations
- **Context Awareness**: References to previous questions
- **Error Handling**: Graceful error messages

### **❌ Issues to Report**
- **Session Creation Failures**: API errors
- **Context Loss**: Previous questions not remembered
- **Poor Citations**: Malformed legal citations
- **Low Quality Responses**: Generic or irrelevant answers
- **UI Issues**: Interface problems

---

## 🚀 **Quick Start Testing**

### **1. Open Browser**
- Go to: `http://127.0.0.1:8000/qa/`

### **2. Test Basic Functionality**
- Click "What is a writ petition?" sample question
- Wait for response
- Check for session ID and model info

### **3. Test Conversation Memory**
- Ask: "What are the requirements for filing it?"
- Verify follow-up detection
- Check context awareness

### **4. Test Advanced Features**
- Ask complex legal question
- Check citation formatting
- Verify GPT-4 responses

### **5. Check System Status**
- Go to: `http://127.0.0.1:8000/qa/status/`
- Verify all components are working

---

## 🎉 **Expected Results Summary**

After testing, you should see:

✅ **Modern Chat Interface**: WhatsApp-like conversation UI
✅ **Session Management**: Automatic session creation and tracking
✅ **Follow-up Detection**: "Follow-up" badges on relevant responses
✅ **GPT-4 Responses**: High-quality, structured legal analysis
✅ **Professional Citations**: Proper legal citation formatting
✅ **Context Awareness**: AI remembers previous conversation
✅ **Error Handling**: Graceful fallbacks and error messages
✅ **Mobile Responsive**: Works on all device sizes

---

**🎯 Start with the main interface at `http://127.0.0.1:8000/qa/` and test the conversation features!**
