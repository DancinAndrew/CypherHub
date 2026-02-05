# CypherHub - 街舞活動整合平台 (The Street Dance Event Platform)

## 📖 專案簡介 (Introduction)

**CypherHub** 是一個專為街舞圈打造的活動資訊整合與售票平台（像是街舞版的 Accupass）。

目前街舞圈的 Battle、成發、Workshop 資訊散落在 Facebook 社團、Instagram 限時動態與各大工作室網站，導致舞者難以搜尋特定舞風或日期的活動。GroovePass 致力於解決這個問題，提供一個集中化、可篩選且支援金流購票的平台。

### 核心問題解決 (Problem Solved)
- **資訊碎片化**：整合 FB/IG 零散資訊。
- **搜尋困難**：提供「舞風 (Style)」、「地區 (Location)」、「日期 (Date)」的精確篩選（如：只找 Popping Battle）。
- **報名繁瑣**：整合金流與報名系統，取代傳統的 Google 表單 + 匯款後五碼對帳。

## 🛠 技術堆疊 (Tech Stack)

- **Backend Framework**: Python Flask
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migration**: Flask-Migrate
- **Payment Integration**: (預計串接 綠界 ECPay / 藍新 NewebPay / Stripe)
- **Frontend**: Jinja2 Templates + Bootstrap/Tailwind (或是 React/Vue，視開發階段而定)
- **Deployment**: Docker / Heroku / Render / AWS

## ✨ 功能特色 (Features)

### MVP (最小可行性產品)
- [ ] **活動瀏覽**：依照舞風 (HipHop, Popping, Locking, Breaking, Waacking...) 篩選活動。
- [ ] **活動詳情**：包含 Judge, DJ, MC, 報名費, 賽制等詳細資訊。
- [ ] **會員系統**：主辦方與參加者註冊/登入 (支援 OAuth Google/FB)。
- [ ] **線上購票**：整合金流，支援信用卡/ATM 轉帳。
- [ ] **電子票券**：購買後生成 QR Code 入場券。

### 三、 開發方向建議 (Development Roadmap)

**"Database First"** 的策略，先把資料結構定好，因為街舞活動的屬性很複雜。

#### 1. 資料庫設計重點 (Schema Design)
這是你最核心的部分。你需要思考 `Events` 表格如何設計：
* **Dance Styles (舞風)**: 這是最重要的 Tag。一個活動可能同時有 Popping 和 Locking，所以是 Many-to-Many 關係。
* **Roles (角色)**: 活動會有 Judge, DJ, MC, Host，這些最好也是結構化的資料，方便以後搜尋「某個老師當評審的活動」。
* **Ticket Types (票種)**: 比賽選手票 (Battle/Audition)、觀賽票 (Audience)、早鳥票、團體票。

#### 2. 金流串接策略 (Payment)
既然你要做台灣市場，**綠界 (ECPay)** 或 **藍新 (NewebPay)** 是避不掉的。
* **難點**：這些金流通常需要企業戶才能用完整功能，個人戶限制較多。開發測試階段可以使用他們的「測試環境 (Sandbox)」。
* **流程**：建立訂單 -> 送出表單到金流商 -> 使用者刷卡 -> 金流商 Callback (Webhook) 回你的 Server -> 你更新訂單狀態為「已付款」 -> 發送 QR Code。

#### 3. QR Code 驗票
既然是 Accupass 模式，線下驗票很重要。
* 你需要做一個簡單的「後台驗票頁面」，主辦方可以用手機掃描參賽者的 QR Code，你的 Server 驗證後回傳「驗票成功」。

---

### 四、 待辦事項清單 (Todo List)

#### Phase 1: 基礎架構與資料顯示 (只讀不寫)
* [ ] **環境建置**：安裝 Flask, PostgreSQL, 設定 Git repo。
* [ ] **資料庫規劃**：設計 User, Event, Ticket, Order, Category(舞風) 的 Schema。
* [ ] **資料庫連線**：設定 SQLAlchemy 與 Flask-Migrate。
* [ ] **種子資料 (Seeding)**：手動建立幾個範例活動資料（例如：Ocean Battle Session, Poplock Park）。
* [ ] **首頁開發**：顯示活動列表卡片。
* [ ] **搜尋/篩選功能**：實作「依舞風篩選」、「依日期排序」的功能。
* [ ] **活動內頁**：顯示活動詳細資訊 (海報、地點、時間、介紹)。

#### Phase 2: 會員與主辦方系統
* [ ] **會員註冊/登入**：實作 Flask-Login，區分一般使用者與主辦方。
* [ ] **主辦方後台**：讓主辦方可以 CRUD (新增/修改/刪除) 自己的活動。
* [ ] **圖片上傳**：整合 AWS S3 或 Imgur API，讓主辦方上傳活動海報。

#### Phase 3: 票務與金流 (最困難的階段)
* [ ] **購物車/下單邏輯**：選擇票種、數量，建立「待付款」訂單。
* [ ] **金流串接 (ECPay/NewebPay)**：閱讀官方 API 文件，實作付款請求。
* [ ] **Webhook 處理**：實作接收金流商「付款成功通知」的 API，並更新資料庫狀態。
* [ ] **票券生成**：訂單成立後，生成唯一的 UUID 並轉為 QR Code。
* [ ] **Email 通知**：寄送購票成功通知信與 QR Code 給使用者。

#### Phase 4: 優化與社群功能
* [ ] **我的票券頁面**：使用者查詢歷史訂單與即將參加的活動。
* [ ] **收藏/追蹤**：使用者可以收藏有興趣的活動。
* [ ] **活動分享**：一鍵生成漂亮的分享圖卡 (Open Graph meta tags)。
* [ ] **部署上線**：購買網域，部署到雲端伺服器。
