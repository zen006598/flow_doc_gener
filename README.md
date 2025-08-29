# Flow Documentation Generator

一個基於 AI 的程式碼分析工具，能自動生成 C# 專案的完整流程文件、呼叫鏈分析和 Mermaid 流程圖。

## 功能特色

- 🔍 **自動程式碼分析**：使用 Tree-sitter 解析 C# 程式碼結構  
- 🤖 **AI 智能分析**：基於 Gemini API 進行功能分析和文件生成
- 📊 **呼叫鏈追蹤**：完整追蹤方法呼叫關係和相依性  
- 📈 **流程圖生成**：自動生成 Mermaid 格式的流程圖
- 📚 **技術文件**：生成企業級的技術參考手冊
- ⚡ **快取機制**：支援增量分析，提升執行效率
- 🎯 **靈活配置**：支援自訂入口點和檔案過濾規則

## 系統需求

- Python 3.13.5+
- uv（Python 套件管理工具）
- Gemini API 金鑰

## 安裝步驟

### 1. 安裝 uv
refer: [uv](https://github.com/astral-sh/uv)

### 2. 設定專案
```bash
# 複製專案
git clone <repository-url>
cd flow_doc_gener

# 安裝相依套件
uv sync
```

### 3. 環境變數設定
建立 `.env` 檔案：
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

## 使用方式

### 基本使用
```bash
# 分析指定資料夾的 C# 專案
uv run main.py --dir /path/to/your/csharp/project
```

### 進階參數

#### 檔案過濾
```bash
# 自訂包含的檔案類型
uv run main.py --dir /path/to/project -i "*.cs" "*.cshtml"

# 排除特定檔案或資料夾  
uv run main.py --dir /path/to/project -e "test*" "bin/*" "obj/*"
```

#### 指定入口點
```bash
# 分析特定的控制器方法
uv run main.py --dir /path/to/project --target-func "UserController.GetUser"

# 分析多個入口點
uv run main.py --dir /path/to/project --target-func "UserController.GetUser" "OrderController.Create"
```

#### 語言設定
```bash
# 生成中文文件
uv run main.py --dir /path/to/project --lang "中文"

# 生成英文文件  
uv run main.py --dir /path/to/project --lang "english"
```

#### 快取管理
```bash
# 重複使用現有分析結果
uv run main.py --dir /path/to/project --run-id "20250829T143052Z"
```

## 輸出結果

執行完成後，會在以下位置產生檔案：

```
output/
└── {run_id}/
    ├── UserController.GetUser.md      # 技術文件
    ├── OrderController.Create.md      # 技術文件  
    └── ...

cache/
└── {run_id}/
    ├── src.json                       # 原始碼快取
    ├── func_map.json                  # 函數對應表
    ├── dep.json                       # 相依關係
    ├── entry.json                     # 入口點資訊
    ├── call_chain.json                # 呼叫鏈分析
    ├── feat.json                      # 功能分析
    ├── chart.json                     # 流程圖資料
    └── feat_status.json               # 處理狀態
```

## 架構說明

### 核心元件

- **Pipeline**：主要執行流程控制
- **Analyzer**：程式碼結構分析（基於 Tree-sitter）
- **Agent**：AI 分析代理（使用 Autogen 框架）  
- **Model**：資料模型和快取管理（基於 TinyDB）
- **Service**：業務邏輯服務層

### 分析流程

1. **原始碼爬取**：掃描和壓縮原始碼檔案
2. **函數對應**：建立檔案與函數的對應關係
3. **相依性分析**：分析程式碼間的呼叫關係
4. **入口點檢測**：識別 API 端點和重要方法  
5. **呼叫鏈分析**：使用 AI 追蹤完整呼叫路徑
6. **功能分析**：AI 分析功能特性和資料流
7. **圖表生成**：生成 Mermaid 流程圖
8. **文件產出**：生成完整的技術文件
