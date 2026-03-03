**企業文件問答系統（RAG 架構）**

主要想練習RAG整體流程，達到可以上傳文件、建立向量索引、做語意搜尋再根據搜尋結果生成回答。



**系統架構**使用三個核心元件：

PostgreSQL：儲存文件與文字內容（原始資料來源）

Qdrant：儲存文字向量，用於語意搜尋

OpenAI：負責向量生成（Embedding）與回答生成（LLM）



**文件處理流程：**

上傳文件→ 切成多個 chunk→ 建立索引 →轉成向量→ 存入向量資料庫



**使用者提問流程：**

問題轉向量→ 向量搜尋→ 找到相關段落→ 從資料庫取回完整內容→ 組成上下文→ 傳給 LLM→ 回傳回答



**技術使用**

Python 3.12

Django + DRF

PostgreSQL

Qdrant

OpenAI API

Docker Compose

整個環境用 Docker 管理，確保不會因為本機環境不同而出問題。



可以做的事情

1\. 上傳文件

POST /api/documents/

2\. 建立索引

POST /api/documents/{id}/index/

3\. 語意搜尋

POST /api/search/

4\. 問答

POST /api/ask/



我在這個專案中學到的

* Docker container 與 volume 的差別
* 向量資料庫與關聯式資料庫的角色分工
* 如何處理 404 / 500 錯誤
* 如何閱讀 traceback 找錯誤來源
* OpenAI quota 與 API 錯誤處理
* RAG 的完整流程拆解



**執行前需要安裝**

**1. Docker Desktop（必要）**

本專案使用 Docker 管理所有環境（Python、Django、PostgreSQL、Qdrant）。

請先安裝：https://www.docker.com/products/docker-desktop/

**2. OpenAI API Key（必要）**

本專案需要 OpenAI 產生向量與回答。

請在專案根目錄建立 .env 檔案：OPENAI\_API\_KEY=你的API金鑰



🔹 如何啟動系統

1️⃣ 開啟 PowerShell



2️⃣ 進入專案資料夾

cd <your-project-path>

請改成你自己的專案路徑。



3️⃣ 啟動 Docker

docker compose up -d



4️⃣ 確認系統是否正常

打開瀏覽器：http://localhost:8000/health/

如果看到：{"status":"ok","db":1}

代表：Django 正常 PostgreSQL 正常 Docker 正常



🔹 關閉系統

docker compose down

