===========================================================================
Enterprise QA System (RAG 企業文件問答系統後端 API)
===========================================================================

本專案是一個基於 RAG (檢索增強生成) 架構的企業文件問答系統後端服務。開發本專案的核心目的在於完整實作 RAG 的技術鏈，包含文件的動態上傳、文本分段(Chunking)、向量化儲存(Embedding Indexing)、語意檢索以及動態 Context 提示詞生成。

本專案專注於後端架構與資料流實作，完全採用 Docker Compose 進行容器化管理，並利用 Django ORM 進行關聯式資料庫的控制，確保開發與部署環境的一致性與可擴充性。

---------------------------------------------------------------------------
1. 系統架構與角色分工
---------------------------------------------------------------------------
本系統由三個核心元件協同運作：

* PostgreSQL：
  關聯式資料庫，由 Django ORM 進行資料庫管理。負責儲存原始文件的元數據(Metadata，如檔名、上傳時間)與切分後的文字區塊(Chunks)，作為系統的真實資料來源。

* Qdrant：
  向量資料庫，儲存由文字轉化而來的向量特徵(Embedding)，並採用 Cosine (餘弦相似度) 演算法進行語意搜尋。

* OpenAI API：
  負責呼叫 text-embedding-3-small 產生向量，並在問答階段調用語言模型(LLM)生成最終的脈絡化回答。


[資料流與技術流程]

A. 知識庫建置流水線 (Data Pipeline)
上傳 PDF/文字文件 -> 文本分段 (Chunking) ->
   ├──> 使用 Django ORM 寫入 PostgreSQL (儲存原始內文)
   └──> 呼叫 OpenAI Embedding -> 寫入 Qdrant (儲存向量索引)

B. 使用者問答檢索流程 (RAG Flow)
使用者提問 -> 轉換為問題向量 -> Qdrant 語意搜尋 -> 撈取 Top-K 相關段落
   ├──> 組裝 Context + Prompt -> 傳給 OpenAI (LLM) -> 回傳答案

---------------------------------------------------------------------------
2. 技術棧 (Tech Stack)
---------------------------------------------------------------------------
* 程式語言與框架：Python 3.12, Django REST Framework (DRF)
* 資料庫元件：PostgreSQL, Qdrant (Vector Database)
* AI 開發套件：OpenAI API
* 虛擬化部署：Docker, Docker Compose

---------------------------------------------------------------------------
3. API 端點說明
---------------------------------------------------------------------------
本專案為純後端 API 服務，支援透過 Postman 或 cURL 進行接口測試與資料驗證：

* 功能 1：上傳文件
  - HTTP 方法：POST
  - URL 端點 ：/api/documents/
  - 說明     ：上傳原始文件並透過 Django ORM 寫入 PostgreSQL。

* 功能 2：建立索引
  - HTTP 方法：POST
  - URL 端點 ：/api/documents/{id}/index/
  - 說明：將指定文件進行 Chunking、向量化並大量寫入(Upsert)至 Qdrant。

* 功能 3：語意搜尋
  - HTTP 方法：POST
  - URL 端點 ：/api/search/
  - 說明 ：輸入查詢字串，返回 Qdrant 檢索出關聯度最高的文字段落。

* 功能 4：知識庫問答
  - HTTP 方法：POST
  - URL 端點 ：/api/ask/
  - 說明：結合語意檢索與 LLM，生成限制文本來源的準確回答。

提示：防禦性設計
系統在執行索引建立或檢索時，後端會自動觸發 ensure_collection() 機制，自動檢查並建立 Qdrant 的 Collection 規格。

---------------------------------------------------------------------------
4. 專案收穫與工程實踐
---------------------------------------------------------------------------
在此專案的開發與 Debug 過程中，我掌握了以下核心後端思維與技能：

* 分散式資料架構：理清關聯式資料庫與向量資料庫（儲存特徵用於相似度檢索）的角色分工與協同作業。
* Django ORM 實務應用：透過 Django Model 定義一對多(One-to-Many)的文件與文字區塊(Chunks)關聯，並掌握 makemigrations 與 migrate 進行資料庫版本控制。
* Docker 虛擬化應用：深入理解 Docker Container 運行生命週期、容器間網路連線與 Volume 持久化儲存的設定。
* 異常與防禦性編程：實作了針對 OpenAI API 額度限制(Quota Exceeded)與網路逾時的錯誤處理機制，並強化了閱讀 Django Traceback 結構化排錯的能力。

---------------------------------------------------------------------------
5. 快速開始 (How to Run)
---------------------------------------------------------------------------
[前提條件]
1. 電腦需安裝 Docker Desktop ( https://www.docker.com/products/docker-desktop/ )
2. 準備一組可用的 OpenAI API Key

[Step 1: 配置環境變數]
請在專案根目錄下建立一個名為 `.env` 的檔案，並填入以下內容：

OPENAI_API_KEY=你的OpenAI金鑰
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=enterprise_docs

[Step 2: 啟動系統與資料庫遷移]
開啟終端機（PowerShell 或 Terminal），進入專案資料夾並依序執行以下指令：

# 1. 建立並在背景啟動所有 Docker 容器 (Django, PostgreSQL, Qdrant)
docker compose up -d

# 2. 執行 Django 資料庫遷移，讓 Django ORM 自動在 PostgreSQL 中建立所需的資料表
docker compose exec web python manage.py migrate

(註：若您 docker-compose 中的 Django 服務名稱不為 web，請將上面指令中的 web 替換為對應名稱。)

[Step 3: 健康檢查]
系統啟動後，可透過瀏覽器或 Postman 訪問健康檢查端點：
http://localhost:8000/health/

若看見以下 JSON 回應，代表所有容器與關聯資料庫皆正常連線運行：
{"status":"ok","db":1}

[關閉系統]
若需停止所有容器服務，請於專案目錄執行：
docker compose down
===========================================================================