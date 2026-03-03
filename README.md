**企業文件問答系統（RAG 架構）**

主要想練習RAG整體流程，達到可以上傳文件、建立向量索引、做語意搜尋再根據搜尋結果生成回答。



**系統架構**使用三個核心元件：

PostgreSQL：儲存文件與文字內容（原始資料來源）

Qdrant：儲存文字向量，用於語意搜尋

OpenAI：負責向量生成（Embedding）與回答生成（LLM）



**文件處理流程：**

上傳文件→ 切成多個 chunk→ 轉成向量→ 存入向量資料庫



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





