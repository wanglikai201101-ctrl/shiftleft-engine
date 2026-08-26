# ShiftLeft Engine · 左移·來福

> **輸入需求,剩下交給 AI。**

> 一套需求驅動的測試左移工程平台 —— 從源代碼與需求出發,自動產出可追溯的知識庫文件(10 維度)、雙向追溯圖譜與 MCP-Ready 測試用例。本期以「GSD Knowledge Base 開源子集」形式發布。

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python](https://img.shields.io/badge/Python-3-blue.svg)](https://www.python.org/)
[![Claude Code Skills](https://img.shields.io/badge/Claude%20Code-Skills-orange.svg)](https://claude.com/claude-code)

> **🌐 多語言版本 / Languages**: [簡體中文](README.md) · **繁體中文** · [English](README.en.md) · [日本語](README.ja.md)

## 🎬 演示影片

[點擊觀看完整演示](https://youtu.be/stfLoSjn8Go)

> 🧪 **一次完整流水線實測:130 個 agent · 耗時 1h01m · 狀態 done(非 fail)** —— 編碼前調查 → 前後端開發+自動檢查 → 文件/圖譜維護 → 自動維運部署 → 冒煙測試 → 真實 UAT → 報告,全流程真實跑通,截圖見下。

## 🧩 什麼是 ShiftLeft Engine?

ShiftLeft Engine 是一套**需求驅動的測試左移工程平台**(持續更新中),本期開源的是其中真實可用、可獨立部署的一環:**GSD Knowledge Base** —— 把「從需求到驗證」裡最根基的工程能力開放出來,讓每個團隊都能在自己的專案上落地 **需求 → 研發 → 文件 → 圖譜 → 測試用例** 的自動化鏈路:27 個自研 `gsd-kb-*` skills 涵蓋 需求/文件/圖譜/測試用例 的知識庫工程與用例生成;另含 **9 個 gsd-core(MIT)研發技能**(quick/debug/spike/code-review/plan-phase/execute-phase 等,啟發自 gsd-core、按需取用、未完整沿用),補足 研發/工程方法 側面。

### 核心理念

> **輸入一句話,剩下的交給 AI。**
>
> 這是 AI 時代下的新典範:**AI 是執行的主力**——從需求到編碼、測試、文件、部署,由 AI 全程自動執行、自動維護、自動自癒。
>
> 人只負責輸入需求與驗收結果。**由 AI 驅動的測試左移**,讓品質從源頭被保障,全鏈路可追溯。

### 🚧 當前狀態

> 以下為**完整工程已實現**的能力(本開源子集只含其中的 KB 工程層,見「本期開放能力」與「為什麼只開源輪子」)。

- ✅ **完整流水線**:輸入需求 → 確認變更模塊 → 擴寫需求(現狀調查) → 代碼調查產出 Plan → 按 Plan 快速開發(過程中首次自動檢查)→ 開發完成後並行 Fill(圖譜 + 文件 + 自動維運 + 元素指紋追加)→ 冒煙測試(失敗則持續修復)→ UAT 測試(忠於需求 / 忠於品質)→ 報告
- ✅ 圖譜視覺化(離線 D3 交互式圖譜)
- ✅ AI 輔助修復(冒煙 / UAT 失敗自動修復)
- 🔄 持續優化:測試涵蓋率分析
- 📋 規劃中:更多語言支持;後期再增一輪 UAT,失敗則二次修復輪詢

### 🎯 未來規劃

- **Phase 1**: 測試左移工程平台(當前)
- **Phase 2**: 應用到 App 開發層(規劃中)
  - 將此模式擴展到移動端開發
  - 實現需求 → 編碼 → 測試 → 發布 的完整閉環
  - 支持 iOS/Android/Flutter 等跨平台開發

> **這是一個持續演進的專案,歡迎關注和參與!**

---

## 🖼️ 完整流水線跑通截圖(真實運行證據)

> 以下截圖來自一次完整流水線實測(**130 個 agent · 1h01m · 狀態 done**),按階段排列。
> 註:「編碼→部署→冒煙→UAT→報告」閉環屬產品完整願景(自動化部署能力本期未隨開源子集發布),截圖用於展示完整產品真實跑通;本開源子集可獨立運行的能力見「本期開放能力」。

| ① 編碼前調查 | ② 前後端開發 + check | ③ 文件維護 |
|---|---|---|
| ![編碼前調查](docs/101编码前的调查.jpg) | ![前後端開發+check](docs/102前后端开发+check.jpg) | ![文件維護](docs/103文档维护.jpg) |

| ④ 圖譜維護 | ⑤ 自動維運部署 | ⑥ 冒煙測試 |
|---|---|---|
| ![圖譜維護](docs/104维护图谱.jpg) | ![自動維運部署](docs/105自动运维部署.jpg) | ![冒煙測試](docs/106冒烟测试.jpg) |

| ⑦ 真實 UAT 測試 | ⑧ UAT 測試結果 | ⑨ 產生報告 |
|---|---|---|
| ![真實UAT測試](docs/107真实UAT测试.jpg) | ![UAT測試結果](<docs/111 UAT-测试结果.jpg>) | ![產生報告](docs/108产生报告.jpg) |

| ⑩ 知識庫 + 圖譜 | ⑪ 文件具像化 | ⑫ 完整報文 |
|---|---|---|
| ![知識庫+圖譜](docs/109知识库+图谱.jpg) | ![文件具像化](docs/110文档具像化.jpg) | ![完整報文](docs/113完整报文.jpg) |

| ⑬ trce 為證 | ⑭ 影片為證 |
|---|---|
| ![trce為證](docs/111视频-trce为证.jpg) | ![影片為證](docs/112视频为证.jpg) |

---

## 🧩 為什麼只開源「輪子」?——拼圖,完整地放在這裡

不是不想交付整列火車,而是刻意只開源這一層:**我把整列「測試左移工程平台」的火車拆成一張完整拼圖,每一塊拼圖(輪子)都放到這裡**——「需求 → 研發 → 文件 → 圖譜 → 測試用例」自動化鏈路的所有可重用組件:27 個 `gsd-kb-*` skills + Python 引擎 + 9 個 gsd-core(MIT)研發技能。每一塊都能獨立安裝、獨立使用。

> 把這些輪子一塊塊拼起來,搭出來的,就是上面影片裡那列**真實跑過 130 個 agent · 61 分鐘 · 全鏈路 done** 的測試左移工程平台——一張拼圖,一輛完整的火車。

> 把拼圖完整地放在這裡,不為別的,是為了找到**志同道合的人**:看得見這列「測試左移工程平台」火車,也願意動手把拼圖一塊塊拼上軌道的人。

> 輪子已經給到大家了。如果明知道拼起來就是一列完整的火車,卻只想看看、不想動手——那這列火車,就只好從你身邊開走了 😄

**這列火車長什麼樣?** → [演示影片](https://youtu.be/stfLoSjn8Go) + 上文 14 張真實運行截圖。

> **本期範圍**:上面的拼圖(輪子)都已在本倉庫交付、可獨立拼裝;更上游的「端到端自動編排與部署」車頭,屬於完整產品的後續迭代。想拼整列火車的人,從這些拼圖動手,就是上車最快的路。

---

## 🎯 為什麼需要 Fill?

### 痛點:傳統開發的問題

```
❌ 口頭約定:PM說"這裡要加個欄位"
   → 開發加了
   → 測試不知道
   → 三個月後沒人記得為什麼

❌ AI 專案黑盒:
   → AI 做了半年專案
   → 代碼能跑
   → 但沒人知道為什麼這麼設計
   → 無法維護,只能重寫

❌ 無法溯源:
   → 需求變更了
   → 不知道影響哪些介面
   → 不知道影響哪些測試
   → 只能全量回歸,浪費時間
```

### 解決方案:Fill 雙向追溯圖譜

```
需求 (REQ-xxx)
    │
    ├──→ 介面 (API-xxx)
    │       │
    │       ├──→ 資料庫 (Table-xxx)
    │       │       │
    │       │       └──→ 欄位級讀寫追溯
    │       │
    │       └──→ 前端頁面 (Page-xxx)
    │               │
    │               └──→ UI 元素 (data-testid)
    │
    └──→ 測試點 (TP-xxx)
            │
            ├──→ API 測試用例
            ├──→ UI 測試用例
            └──→ E2E 測試用例
```

### Fill 的真正價值

| 追溯方向 | 價值 | 服務對象 |
|---------|------|----------|
| 需求 → 介面 | 這個需求實現了哪些介面? | 開發、測試、PM |
| 介面 → 資料庫 | 這個介面讀寫了哪些表? | 開發、DBA |
| 介面 → 頁面 | 哪些頁面呼叫了這個介面? | 前端、測試 |
| 需求 → 測試點 | 這個需求需要測什麼? | 測試 |
| 變更 → 影響 | 改了這個介面,影響哪些需求? | 全員 |
| 測試 → 回歸 | 這個測試涵蓋了哪些需求? | 測試、PM |

### 為什麼 Fill 放在中間?

- **編碼後**:有代碼可以提取文件
- **測試前**:圖譜決定測試範圍
- **維護時**:圖譜記錄設計決策

### 核心價值

> **讓 AI 的執行全鏈路可追溯。**
>
> - 需求有據可查
> - 研發有圖可依
> - 測試有譜可循
>
> **這就是為什麼中間放 Fill 階段的原因!**

---

## ⚖️ 誠實性原則

測試左移有一個關鍵的**誠實性問題**:

### 兩種測試策略

| 策略 | 做法 | 首次成功率 | 說明 |
|------|------|-----------|------|
| **忠於需求** | 沒說的不測 | ~95% | 只測需求明確要求的 |
| **追求品質** | 自由發揮 | ~70% | 還要測邊界、異常、效能等 |

### 為什麼忠於需求能有 95% 成功率?

```markdown
# 需求:建立訂單成功後回傳 order_id
✅ 測試:POST /api/orders → 200 + order_id

# 需求沒說:並發建立怎麼辦
❌ 不測:並發衝突處理(除非需求明確要求)

# 需求沒說:超大金額怎麼辦
❌ 不測:金額邊界(除非需求明確要求)
```

### 建議

- ✅ 需求明確要求的 → 100% 測試
- ⚠️ 需求隱含的 → 95% 涵蓋
- ❌ 需求沒說的 → 不測(除非單獨約定)

**為什麼?**
- 測試左移的目標是「快速驗證需求是否實現」
- 不是「追求代碼完美」
- 如果要追求品質,需要額外的「品質增強」階段

---

## 🔄 本期開放能力 · KB 工程化工作流

完整的「需求 → 編碼 → 部署 → 冒煙 → UAT → 報告」自動化閉環是 ShiftLeft Engine 的**產品完整願景**,其編排流水線按完整產品節奏迭代,**本期不隨本倉庫發布**。本期開放的是這條閉環裡最根基的「知識庫 + 圖譜 + 測試用例生成」工程層,由 **27 個 `gsd-kb-*` skills** 與 **9 個 gsd-core(MIT)研發技能** 組成,可直接落地:

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1 · 初始化 KB + 圖譜                                        │
│  /gsd-kb-init --source <代碼> --module <模塊> --output docs/kb   │
├─────────────────────────────────────────────────────────────────┤
│  Step 2 · 多維度 Fill(文件 + 圖譜)                              │
│  /gsd-kb-fill + 14 個 fill 子技能(10 維度文件 + 圖譜)           │
├─────────────────────────────────────────────────────────────────┤
│  Step 3 · 測試用例生成(MCP-Ready JSON)                           │
│  /gsd-kb-gen-tests-{api,e2e,ui}                                 │
├─────────────────────────────────────────────────────────────────┤
│  Step 4 · 元素指紋注入                                            │
│  /gsd-kb-enforce-locators(data-testid 標準化)                   │
├─────────────────────────────────────────────────────────────────┤
│  Step 5 · 查詢 · 修復 · 增量吸收                                  │
│  /gsd-kb-query · /gsd-kb-repair-orphans · /gsd-kb-absorb         │
└─────────────────────────────────────────────────────────────────┘
```

### Step 1:初始化(init)

```
源代碼 → 反向掃描 API/表/頁面/任務 → 生成文件骨架 + 圖譜
/gsd-kb-init --source C:/Code/your-project --module your-project --output docs/kb
```

### Step 2:多維度填充(fill)

```
文件骨架
    │
    ├──→ Phase 1:/gsd-kb-fill-tech      ← Python 引擎 batch-fill(秒級 AST 靜態提取)
    └──→ Phase 2:/gsd-kb-fill-ai        ← AI multi-agent 編排(分鐘級深度語義填充)
          ├── 10 維度文件:requirements · apis · storage · pages · jobs
          │             config · permissions(認證授權)· error-handling · integration · tech
          ├── 擴展:from-prd(需求原文吸收,填充權威業務上下文)
          └── 圖譜:graph(構建 + 離線 D3 視覺化)· graph-links(雙向追溯鏈回填)
```

### Step 3:測試用例生成(gen-tests)

```
/gsd-kb-gen-tests-api    → 多步驟串聯的 API 契約用例(MCP-Ready JSON)
/gsd-kb-gen-tests-e2e    → 基於 depends_on DAG 的業務流 / 邊緣場景 / 回滾一致性用例
/gsd-kb-gen-tests-ui     → 基於 data-testid 的 UI 用例(Playwright 語義選擇器)
```

模板驅動:每個子 skill 讀 `templates/{API,E2E,UI}-TEST-TEMPLATE.json`,輸出 MCP-Ready 結構化 JSON。執行端在完整產品中由 **QA 多 agent 編排執行系統**承接(准入 → 集群分發 → 真實環境執行 → 結果回流);本期開源子集只開放「用例生成」,執行系統不隨包(後期視開源情況再定)。

### Step 4:元素指紋注入(enforce-locators)

```
掃描前端組件 → 注入標準化 data-testid(交互元素 + 校驗/錯誤提示元素)
→ 讓真實瀏覽器的 UI 測試"快如閃電、穩如磐石"
```

### Step 5:查詢 · 修復 · 吸收

```
/gsd-kb-query            → 圖譜查詢:影響分析 / 需求追溯 / 文件定位,精確上下文
/gsd-kb-repair-orphans   → 修復圖譜孤立連結(孤兒節點,report-only 式核對)
/gsd-kb-absorb           → 把 .planning/ 產物增量吸收進 KB 文件(增量補丁,不整篇重寫)
```

---

## 🏗️ 架構設計

```
┌─────────────────────────────────────────────────────────────────┐
│                  ShiftLeft Engine · 開源子集架構                  │
├─────────────────────────────────────────────────────────────────┤
│  輸入                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  源代碼       │  │   需求文件    │  │  ENV-CONFIG   │          │
│  │ (多語言代碼)  │  │  (REQ-xxx)   │  │  (JSON 契約)  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SKILL 層 · 27 個 gsd-kb-*(Claude Code Skills,Markdown) │   │
│  │  init → fill(+14 子技能) → gen-tests-{api,e2e,ui}      │   │
│  │  enforce-locators → query · repair-orphans · absorb     │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│  ┌──────────────────────┴──────────────────────────────────┐   │
│  │  Python 引擎層 · knowledge-base(packages,12 子命令)     │   │
│  │  零第三方依賴 · scaffold / batch-fill / decompose /     │   │
│  │  fill / check / trace / index / graph / regression      │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│  ┌──────────────────────┴──────────────────────────────────┐   │
│  │  gsd-core(MIT)研發 skills · 9 個                        │   │
│  │  quick · debug · spike · code-review · plan-phase · ... │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  輸出                                                    │   │
│  │  KB 文件(10 維度)· graph.json + graph.html(D3)          │   │
│  │  測試用例 JSON(API/UI/E2E,MCP-Ready)· ENV-CONFIG.json    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

> 完整產品的「🧠 編排層 (Pipeline Orchestrator) + MCP Agent 集群」屬完整產品能力,本期不隨本倉庫發布(演示見上文影片,邊界見「為什麼只開源輪子」)。

---

## 🎯 核心能力

| 能力 | 評分 | 說明 |
|------|------|------|
| Fill 雙向追溯圖譜 | ⭐⭐⭐⭐⭐ | 10 維度全息映射,需求 → 介面 → 儲存 → 頁面 → 測試點全鏈路可追溯 |
| 恆定元素指紋 | ⭐⭐⭐⭐⭐ | data-testid 自動注入(enforce-locators),真實瀏覽器測試快而穩 |
| 測試用例生成 | ⭐⭐⭐⭐⭐ | API / UI / E2E 三格式,模板驅動,MCP-Ready JSON 直接可執行 |
| JSON 契約 | ⭐⭐⭐⭐⭐ | ENV-CONFIG.sample.json 定義部署 → 測試標準契約,下游統一解析 |
| 圖譜查詢 + 影響分析 | ⭐⭐⭐⭐⭐ | gsd-kb-query:變更影響範圍、需求追溯、文件定位,秒級出答案 |
| 孤兒連結修復 | ⭐⭐⭐⭐☆ | graph repair-orphans 自動補邊,排查殘留孤兒節點 |
| 增量吸收 | ⭐⭐⭐⭐☆ | gsd-kb-absorb 增量補丁式吸收,不整篇重寫已有文件 |
| 零第三方依賴引擎 | ⭐⭐⭐⭐⭐ | Python 引擎 12 子命令,純標準庫,一處安裝到處運行 |
| 多棧源解析 | ⭐⭐⭐⭐☆ | scaffold 反向掃描多語言(API/ORM/Page/Job),子專案自動發現 |

---

## 📦 產品組件(設計,隨完整產品迭代公開)

以下 4 個組件是**完整產品**「ShiftLeft Engine」的組件介面設計(隨完整產品迭代公開,未在本倉庫交付):

- **`@shiftleft-engine/fill-graph`** — Fill 雙向圖譜的類型定義與查詢介面(設計)
- **`@shiftleft-engine/locator-generator`** — 元素定位符自動注入工具(設計)
- **`@shiftleft-engine/cli-interface`** — CLI 命令解析與參數校驗規範(設計)
- **`@shiftleft-engine/report-formatter`** — 綜合報告生成模板(設計)

> 早期版本 README 展示的 TypeScript 代碼、npm 包介面與 `shiftleft-engine` 命令行用法,均屬完整產品設計稿(按產品節奏隨後續版本公開)—— 本倉庫真實可用的能力見下方「快速開始」。

---

## 🚀 快速開始

### 安裝

```bash
git clone <本倉庫地址>
cd <本倉庫>
bash install-kb.sh  # 發布倉庫根直接運行; 源碼克隆內為 bash release/install-kb.sh 或 bash scripts/install-kb.sh
```

- 默認 **copy** 模式(安全,倉庫移動不產生斷鏈);`--link` 符號連結(開發模式,改源碼即生效);`--target` 可改目標目錄
- 安裝內容:`gsd-kb-*` skills + 9 個 gsd-core(MIT)研發 skills → `~/.claude/skills`;gsd-core 引擎 → `~/.claude/gsd-core`;Python 引擎 → `~/.claude/knowledge-base`
- 位置說明:27 個 `gsd-kb-*` 在倉庫根 `skills/`;9 個 gsd-core(MIT)研發技能隨發布包提供(源碼克隆為 `release/release-skills/`,發布包根為 `release-skills/`)——倉庫根 `skills/` 只含 27 個 `gsd-kb-*`。完整邊界見 `release/PACKAGE.md`

**安裝完成後重啟 Claude Code**,即可使用 `/gsd-kb-*` 斜線命令。

> 本工程首次開源,安裝或使用中遇到問題,歡迎回饋(提 issue),我會盡快處理。

### 最小可用路徑(init → fill-ai → gen-tests-e2e)

```bash
# 1. 初始化 KB + 圖譜(反向掃描生成文件骨架)
/gsd-kb-init --source C:/Code/your-project --module your-project --output docs/kb

# 2. AI 多代理深度填充(10 維度文件 + 圖譜)
/gsd-kb-fill-ai --module your-project --source C:/Code/your-project/backend \
                --frontend C:/Code/your-project/frontend --output docs/kb

# 3. 生成 MCP-Ready E2E 測試用例
/gsd-kb-gen-tests-e2e --module your-project --output docs/kb
```

### Python 引擎

```bash
cd knowledge-base         # 發布倉庫根; 源碼克隆內為 cd release/knowledge-base
python3 -m packages.cli --help    # 12 個子命令:decompose / fill / check / trace /
                                  # scaffold / batch-fill / graph / index / regression / ...
```

### ENV-CONFIG 契約

部署 → 測試的 JSON 契約範例見 [`samples/ENV-CONFIG.sample.json`](samples/ENV-CONFIG.sample.json);完整發布物邊界見 [`PACKAGE.md`](PACKAGE.md)（源碼克隆內為 `release/PACKAGE.md`）。

---

## 📐 技術棧

- **引擎語言**:Python 3(零第三方依賴,純標準庫)
- **Skill 層**:Claude Code Skills(Markdown 指令 + 模板)
- **資料契約**:JSON(ENV-CONFIG / 測試用例 / graph.json)
- **圖譜視覺化**:D3.js(離線,graph.html 交互式力導向圖)
- **安裝器**:bash(install-kb.sh,開源即裝)

---

## 🤝 貢獻指南

歡迎貢獻!請先閱讀 [`release/PACKAGE.md`](release/PACKAGE.md) 了解開源發布物邊界。

### 開發環境

```bash
# 克隆倉庫(發布時填寫實際倉庫地址)
git clone git@github.com:<your-org>/<repo>.git

# 雙副本同步(重要!)
# skills/ 是源碼,release/skills/ 是發布副本 —— 改 skill 時必須兩處同步,
# 否則發布物與源碼不一致(倉庫 skills 與 ~/.claude 全局副本同理)

# Python 引擎直接在 knowledge-base/ 下運行
cd knowledge-base
python3 -m packages.cli --help
```

---

## 📄 許可證

本專案採用 [Apache License 2.0](LICENSE) 許可證。

**為什麼選擇 Apache-2.0?**
- 寬鬆許可,最大化採用率與社群傳播
- 內含專利授權與商標保護條款,兼顧貢獻者權益
- 與啟發本專案的 gsd-core(MIT)許可證兼容,可保留歸屬聲明

> 本專案包含衍生自 [gsd-core](https://github.com/open-gsd/gsd-core)(MIT License)的內容,詳見 [NOTICE](NOTICE)。

---

## 📊 專案統計

- **Skills**:27 個 `gsd-kb-*`(其中 14 個 fill 子技能,涵蓋 10 維度文件 + 圖譜)
- **Python 引擎**:12 個子命令,零第三方依賴
- **知識圖譜**:10 維度雙向追溯 + 離線 D3 視覺化
- **測試用例**:三格式生成(API / UI / E2E),MCP-Ready JSON
- **研發技能**:內置 9 個 gsd-core(MIT)開發技能

---

## 🔗 相關連結

- [演示影片](https://youtu.be/stfLoSjn8Go)
- [開源發布物說明](release/PACKAGE.md)

---

## 🙏 致謝

### 靈感來源

本專案的架構設計和部分工具函數借鑑了以下優秀開源專案:

- **[GSD Core](https://github.com/open-gsd/gsd-core)** - 元提示、上下文工程和規範驅動開發系統
  - 本專案的知識圖譜查詢、文件生成等能力受 GSD Core 啟發
  - 研發側 skills(gsd-quick / gsd-debug / gsd-spike / gsd-code-review / gsd-plan-phase 等 9 個)直接內嵌自 gsd-core
  - GSD Core 採用 MIT 許可證,本專案對其致以誠摯感謝

### 技術棧致謝

感謝以下開源專案:
- [Python](https://www.python.org/)
- [D3.js](https://d3js.org/)
- [Claude Code](https://claude.com/claude-code)
- [Bash](https://www.gnu.org/software/bash/)

---

## 🗺️ 路線圖

### 已完成

- ✅ 需求驅動 KB 工程化流水線(gsd-kb-init → fill → graph)
- ✅ Fill 雙向追溯圖譜(10 維度 + 離線 D3 視覺化)
- ✅ 圖譜視覺化(graph.html 交互式力導向圖)
- ✅ 恆定元素指紋(data-testid 注入,enforce-locators)
- ✅ API / UI / E2E 測試用例生成(MCP-Ready JSON)
- ✅ AI 輔助修復(冒煙 / UAT 失敗自動修復)
- ✅ Python 引擎 12 子命令(零第三方依賴)
- ✅ 一鍵安裝器(install-kb.sh)

### 進行中

- 🔄 測試涵蓋率分析(coverage 深化)

### 規劃中

- 📋 QA 多 agent 編排執行系統(測試左移執行端,後續視開源情況決定)
- 📋 npm 分發 `@shiftleft-engine` 組件(開源子集 → 獨立包)
- 📋 更多語言支持
- 📋 後期:UAT 通過後再增一輪 UAT,失敗則二次修復輪詢
- 📋 效能測試整合(K6)
- 📋 移動端 App 開發支持(Phase 2)
- 📋 多人協作模式

### 未來願景(Phase 2)

> **將此模式應用到 App 開發層**
>
> - 實現需求 → 編碼 → 測試 → 發布 的完整閉環
> - 支持 iOS/Android/Flutter 等跨平台開發
> - 整合 CI/CD 流水線
> - 支持多團隊協作

---

## 💬 聯絡方式

- **電子郵件**: wanglikai201101@gmail.com
- **GitHub**: [@wanglikai201101-ctrl](https://github.com/wanglikai201101-ctrl)

---

## 📌 版權聲明

**© 2026 ShiftLeft Engine · Licensed under the Apache License 2.0**

*本倉庫為個人獨立專案,不涉及任何公司商業機密。*

*基於 GSD Core 的啟發進行架構設計,感謝原作者的開源貢獻。*