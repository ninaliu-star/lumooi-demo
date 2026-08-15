"""Nina 的 lumooi Demo 基础简历；版式与内容结构参考当前 CV。"""


DEMO_RESUME_VERSION = "2026-08-13-cv-v7-lumooi-v6-nina"
DEMO_URL = "http://localhost:8503/"


def _bullet(identifier, asset_id, text):
    return {"id": identifier, "asset_id": asset_id, "original": text}


def get_demo_resume():
    return {
        "_demo_version": DEMO_RESUME_VERSION,
        "_editor_settings": {
            "font": "Arial",
            "body_size": 10,
            "name_size": 21,
            "section_size": 11.5,
            "line_height": 1.18,
            "page_margin": 16,
            "section_gap": 10,
            "item_gap": 7,
            "paragraph_gap": 3,
        },
        "profile": {
            "name": "Nina",
            "meta": "lumooi Demo｜个人联系方式已脱敏",
            "contact": "联系方式可在面试沟通时提供",
        },
        "sections": [
            {
                "id": "education",
                "title": "教育经历",
                "entries": [
                    {
                        "title": "Temple University｜国家留学基金委（CSC）全额奖学金公派留学",
                        "subtitle": "Fox School of Business｜M.S. in Innovation Management & Entrepreneurship｜硕士",
                        "location": "费城，美国",
                        "date": "2025.08 – 2026.12",
                        "details": ["核心方向：组织创新机会识别、开放式创新与战略联盟、商业模式创新、精益创业与商业可行性分析。"],
                        "bullets": [],
                    },
                    {
                        "title": "首都经济贸易大学",
                        "subtitle": "劳动经济学院｜人力资源管理专业｜本科",
                        "location": "北京，中国",
                        "date": "2021.09 – 2025.06",
                        "details": [],
                        "bullets": [],
                    },
                    {
                        "title": "Université de Montréal 蒙特利尔大学",
                        "subtitle": "劳资关系｜交换",
                        "location": "魁北克，加拿大",
                        "date": "2024.07 – 2024.08",
                        "details": [],
                        "bullets": [],
                    },
                ],
            },
            {
                "id": "internship",
                "title": "实习经历",
                "entries": [
                    {
                        "title": "互联网科技公司",
                        "subtitle": "招聘 & 招聘运营",
                        "location": "北京，中国",
                        "date": "2024.09 – 2025.03",
                        "bullets": [
                            _bullet("cv_tech_01", "TECH-01", "在承接招聘团队交付 KPI 的同时，兼任招聘运营、雇主品牌及 AI 招聘工具引入调研等项目。独立负责职能岗校招与社招招聘部分岗位，高峰期同步推进约 12–14 个在招岗位。"),
                            _bullet("cv_tech_02", "TECH-01", "负责 HRBP、SSC、培训、行政、财务 BP、财务、公关、筹款顾问等职能岗位招聘，支持团队实现社招关键岗位交付达成率约 95%、基础岗位约 90%；校招 SSP、标准及非标岗位交付达成率均为 100%。"),
                            _bullet("cv_tech_03", "TECH-03", "独立从 0 搭建招聘内容账号，联动设计、公关团队完成内容策划、海报设计、投放及审核流程，账号增长至约 2,300 粉丝；独立策划并落地 200+ 人内部活动。"),
                            _bullet("cv_tech_04", "TECH-10A", "持续优化人才画像与寻访策略，开展目标企业人才 mapping。"),
                            _bullet("cv_tech_05", "TECH-07", "参与 AI 面试工具引入前期调研，协助对接合作团队，撰写市场咨询报告，围绕供应商方案、应用场景、预算投入与招聘效率提升价值进行分析。"),
                        ],
                    },
                    {
                        "title": "会计师事务所",
                        "subtitle": "Talent Team 实习生",
                        "location": "北京，中国",
                        "date": "2023.06 – 2023.09",
                        "bullets": [
                            _bullet("cv_acct_01", "ACCT-01", "支持多地区审计／咨询方向校园招聘，累计推进 100+ 名候选人面试流程，协助关闭 7 个校招岗位；负责候选人沟通、面试安排、流程状态跟进及结果反馈，处理校招学生三方协议签署及解约流程 80+ 份，保障校招录用流程按期推进。"),
                            _bullet("cv_acct_02", "ACCT-03", "参与雇主合作项目、校招宣讲、院校合作沟通及企业开放日等雇主品牌活动，支持现场执行、候选人接待及后续招聘咨询转化。"),
                        ],
                    },
                    {
                        "title": "新媒体互联网公司",
                        "subtitle": "HRBP 实习生",
                        "location": "北京，中国",
                        "date": "2022.06 – 2022.09",
                        "bullets": [
                            _bullet("cv_media_01", "MEDIA-03", "协助培训体系建设，参与培训材料整理、流程跟进及培训执行支持。"),
                            _bullet("cv_media_02", "MEDIA-01", "支持业务团队及人力资源部招聘工作，覆盖销售高级经理、虚拟人设计师、新媒体剪辑师及 HR 实习生等岗位，累计推荐候选人 108 人，业务初筛通过率达 78%，推动 14 人进入 offer／入职流程。"),
                            _bullet("cv_media_03", "MEDIA-01", "通过社交平台推广岗位信息及投递渠道，累计获取增量简历 35+ 份，并转化推荐 8 名候选人，拓展社交媒体招聘获客渠道。"),
                        ],
                    },
                    {
                        "title": "人力资源服务公司",
                        "subtitle": "人力资源部实习生",
                        "location": "北京，中国",
                        "date": "2021.12 – 2022.02",
                        "bullets": [
                            _bullet("cv_hrs_01", "HRS-01", "支持员工关系、招聘交付及入职培训工作，办理正式员工入职、转岗、调岗、离职等手续，累计安排面试 80+ 场、发出 offer 20+ 份，入职转化率达 90%+，并独立完成每周新员工入职宣讲。"),
                        ],
                    },
                ],
            },
            {
                "id": "project",
                "title": "项目经历",
                "entries": [
                    {
                        "title": "lumooi｜个人职业资产系统｜产品设计与开发者",
                        "subtitle": "独立产品项目",
                        "location": "Personal Project",
                        "date": "2026 – 至今",
                        "link": DEMO_URL,
                        "link_label": DEMO_URL,
                        "link_prefix": "Demo",
                        "bullets": [
                            _bullet("cv_lumooi_01", "CP-01", "独立定义并开发以 Experience Bank 为事实底座的个人 Career OS，连接职业资产、职位管理、简历定制、面试准备与申请追踪。"),
                            _bullet("cv_lumooi_02", "CP-02", "使用 Python、Streamlit 与 SQLite 完成本地多页面产品，建立个人版与公开 Demo 的独立数据边界，并持续迭代信息架构、交互流程与数据结构。"),
                        ],
                    },
                ],
            },
            {
                "id": "consulting",
                "title": "咨询经历",
                "entries": [
                    {
                        "title": "HR AI 初创团队咨询项目｜团队成员",
                        "subtitle": "",
                        "privacy_notes": ["公司名称与官网已在公开 Demo 中隐藏"],
                        "location": "费城，美国",
                        "date": "2026.01 – 2026.04",
                        "bullets": [
                            _bullet("cv_cat_01", "CAT-03", "参与为美国 HR AI 初创团队提供战略咨询方案，围绕 AI 人才评估、候选人匹配及一线／初级岗位招聘场景，梳理客户痛点、产品价值主张、目标市场及商业化切入路径。"),
                            _bullet("cv_cat_02", "CAT-04", "支持投资人版商业计划书与融资路演材料优化，参与 TAM／SAM／SOM、竞品格局、GTM 策略、早期融资渠道及投资人叙事逻辑梳理，强化项目面向天使轮／种子轮融资的表达。"),
                            _bullet("cv_cat_03", "CAT-02", "协助梳理 SaaS 商业模式、客户转化路径与增长假设，识别竞争、AI 合规、客户采纳及系统集成等潜在风险，并提出中型企业切入、可解释 AI、轻量化集成等优化建议。"),
                        ],
                    },
                ],
            },
            {
                "id": "competition",
                "title": "竞赛经历",
                "entries": [
                    {
                        "title": "国家级创新研究项目｜成员",
                        "privacy_notes": ["具体竞赛与研究项目名称已隐藏"],
                        "subtitle": "",
                        "location": "",
                        "date": "2022.10 – 2024.06",
                        "bullets": [_bullet("cv_ndc_01", "NDC-02", "基于四川省调研数据，负责文献综述、问卷设计及研究报告整理，获国家级优秀结项。")],
                    },
                    {
                        "title": "省级创新创业项目｜负责人",
                        "privacy_notes": ["具体竞赛项目名称已隐藏"],
                        "subtitle": "",
                        "location": "",
                        "date": "2022.10 – 2024.05",
                        "bullets": [_bullet("cv_yx_01", "", "主导校园兴趣型兼职与实践服务平台项目，完成用户需求分析、竞品调研、SWOT 分析、商业模式设计、财务测算及商业计划书撰写，获省级优秀结项。")],
                    },
                    {
                        "title": "市场研究与商业策划竞赛｜成员",
                        "privacy_notes": ["具体竞赛名称已隐藏"],
                        "subtitle": "",
                        "location": "",
                        "date": "2023.06 – 2023.07",
                        "bullets": [_bullet("cv_camu_01", "", "运用秩和比分析法完成企业命题市场研究，获校级奖项；取得市场分析研究员证书 Level 1。")],
                    },
                ],
            },
            {
                "id": "research",
                "title": "科研经历",
                "entries": [
                    {
                        "title": "人力资源管理方向课题组｜学生研究助理",
                        "subtitle": "",
                        "location": "",
                        "date": "2023.05 – 2025.06",
                        "privacy_notes": ["具体出版物与书稿名称已隐藏"],
                        "bullets": [_bullet("cv_xn_01", "XN-01", "参与两项人力资源与劳动研究类专业书稿写作，负责部分章节研究、案例整理及跨学科材料梳理；出版物名称不在公开 Demo 中呈现。")],
                    },
                    {
                        "title": "人口经济学方向课题组｜学生研究助理",
                        "subtitle": "",
                        "location": "",
                        "date": "2022.09 – 2023.04",
                        "bullets": [_bullet("cv_mzy_01", "MZY-02", "参与女性生育支持政策需求、人口负增长与老年友好型社会建设相关研究，基于课题申报大创项目并获得国家级奖项。")],
                    },
                ],
            },
        ],
    }


DEMO_RESUME = get_demo_resume()
PERSONAL_RESUME_BASE = DEMO_RESUME
