import React, { useState, useEffect } from 'react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip as ChartTooltip, 
  CartesianGrid, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar
} from 'recharts';
import { 
  Wallet, 
  Receipt, 
  TrendingUp, 
  Calendar, 
  Building, 
  Search, 
  RefreshCw, 
  Filter, 
  AlertTriangle, 
  ArrowUpRight, 
  ArrowDownRight,
  Info, 
  ShieldAlert, 
  Award,
  ChevronDown,
  ChevronUp,
  HelpCircle
} from 'lucide-react';

// 定義分類的色彩映射
const CATEGORY_COLORS = {
  '飲食': '#6366f1',    // Indigo
  '交通': '#38bdf8',    // Light Blue
  '娛樂': '#ec4899',    // Pink
  '3C配件': '#f59e0b',   // Amber
  '服飾': '#a855f7',    // Purple
  '醫療': '#10b981',    // Emerald
  '其它': '#64748b'     // Slate
};

// 輔助函式：將數字格式化為貨幣 NT$
const formatCurrency = (val) => {
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(val);
};

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // 圖表切換狀態 (monthly / weekly)
  const [trendMode, setTrendMode] = useState('monthly');
  
  // 發票搜尋與篩選狀態
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [sortBy, setSortBy] = useState('newest'); // newest, oldest, highest, lowest
  
  // 展開的發票號碼集合 (Accordion)
  const [expandedInvoices, setExpandedInvoices] = useState({});

  // 爬蟲同步狀態與日期設定
  const [crawlerLoading, setCrawlerLoading] = useState(false);
  const [crawlerError, setCrawlerError] = useState(null);
  const [crawlerSuccess, setCrawlerSuccess] = useState(false);
  
  // 退貨明細彈出視窗狀態
  const [showRefundModal, setShowRefundModal] = useState(false);
  const [expandedRefundInvoices, setExpandedRefundInvoices] = useState({});
  
  // 獲取過去幾個月前的年月日字串 (格式 YYYY-MM-DD)
  const getPastDateStr = (monthsAgo) => {
    const d = new Date();
    d.setMonth(d.getMonth() - monthsAgo);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };
  
  const getTodayStr = () => {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };
  
  const getEarliestSelectableDateStr = () => {
    const d = new Date();
    // 往回推 8 個月，並將日期設為該月第一天，動態計算 9 個月查詢上限，避免硬編碼
    const targetDate = new Date(d.getFullYear(), d.getMonth() - 8, 1);
    const yyyy = targetDate.getFullYear();
    const mm = String(targetDate.getMonth() + 1).padStart(2, '0');
    return `${yyyy}-${mm}-01`;
  };
  
  // 預設日期區間設為大平台支援的最早歷史日期 (動態計算 9 個月前)，確保初次執行拉取最大量歷史資料！
  const [startDate, setStartDate] = useState(getEarliestSelectableDateStr());
  const [endDate, setEndDate] = useState(getTodayStr());

  useEffect(() => {
    fetchInvoiceData();
  }, []);

  const fetchInvoiceData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 讀取 Python data_cleaner 產出的靜態 JSON 數據
      const response = await fetch('/data/invoice_data.json');
      if (!response.ok) {
        throw new Error('找不到發票數據檔案。請確保已執行過發票下載或同步！');
      }
      const jsonData = await response.json();
      setData(jsonData);
      
      // 動態更新爬蟲起迄預設日期，以「接續抓取未來發生的新發票」為主要目標
      if (jsonData.summary && jsonData.summary.maxDate) {
        setStartDate(jsonData.summary.maxDate);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRunCrawler = async () => {
    setCrawlerLoading(true);
    setCrawlerError(null);
    setCrawlerSuccess(false);
    
    try {
      // 自動使用本地最新發票日期及今天日期範圍進行下載，避免手動輸入
      const latestLocalStr = data?.summary?.maxDate || getEarliestSelectableDateStr();
      const todayStr = getTodayStr();
      
      setStartDate(latestLocalStr);
      setEndDate(todayStr);
      
      const startFormatted = latestLocalStr.replace(/-/g, '/');
      const endFormatted = todayStr.replace(/-/g, '/');
      
      const response = await fetch(`/api/run-crawler?start=${startFormatted}&end=${endFormatted}`);
      if (!response.ok) {
        throw new Error('同步請求失敗，請確認 Vite Dev Server 是否正常運行！');
      }
      
      const result = await response.json();
      if (result.success) {
        setCrawlerSuccess(true);
        // 成功後重新加載數據
        await fetchInvoiceData();
      } else {
        throw new Error(result.stderr || '自動化更新失敗。可能原因：您手動關閉了瀏覽器、登入失敗或下載超時。');
      }
    } catch (err) {
      console.error(err);
      setCrawlerError(err.message);
    } finally {
      setCrawlerLoading(false);
    }
  };

  const renderCrawlerLoadingOverlay = () => (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(15, 23, 42, 0.85)',
      backdropFilter: 'blur(8px)',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      color: '#fff'
    }}>
      <div className="glass-card" style={{
        maxWidth: '500px',
        width: '100%',
        padding: '2rem',
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '1.5rem',
        boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
        border: '1px solid rgba(255,255,255,0.1)'
      }}>
        <div className="kpi-icon-container blue" style={{ width: '64px', height: '64px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <RefreshCw size={32} className="spin" />
        </div>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>機器人正在自動同步發票...</h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>查詢起迄：{startDate} ~ {endDate}</p>
        </div>
        
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.05)',
          borderRadius: '0.75rem',
          padding: '1rem',
          textAlign: 'left',
          fontSize: '0.85rem',
          color: '#d1d5db',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
          width: '100%'
        }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>1.</span>
            <span>已自動開啟財政部大平台的登入網頁。</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>2.</span>
            <span>您的手機號碼與驗證碼已為您預填完成（若已在設定檔中填寫）。</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>3.</span>
            <span style={{ color: '#fca5a5', fontWeight: 600 }}>請在開啟的瀏覽器視窗中，手動輸入「圖形驗證碼」並點擊「登入」！</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>4.</span>
            <span>登入後，機器人將自動設定日期並勾選清單，自動觸發明細 CSV 下載。</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>5.</span>
            <span>下載成功後將自動關閉瀏覽器，呼叫 Pandas 進行資料清洗，完成後此網頁將自動更新！</span>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)', alignItems: 'center' }}>
          <Info size={14} />
          <span>請勿關閉此控制台。查詢歷史發票可能需要 10~30 秒。</span>
        </div>
      </div>
    </div>
  );

  const toggleInvoiceExpand = (invNum) => {
    setExpandedInvoices(prev => ({
      ...prev,
      [invNum]: !prev[invNum]
    }));
  };

  if (loading) {
    return (
      <div className="loading-wrapper">
        <div className="spinner"></div>
        <p>正在加載發票大數據庫...</p>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Pandas 已清洗完成，前端渲染中</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="loading-wrapper" style={{ padding: '3rem', textAlign: 'center', maxWidth: '600px', margin: '100px auto' }}>
        <ShieldAlert size={64} style={{ color: 'var(--danger)', marginBottom: '1rem' }} />
        <h2 style={{ fontFamily: 'Outfit, sans-serif', marginBottom: '1rem', color: 'var(--text-primary)' }}>載入發票數據失敗</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '2rem', lineHeight: '1.6' }}>
          {error || '未偵測到本地 JSON 數據。請先在專案目錄下執行 Python 腳本產生發票檔案！'}
        </p>
        
        {/* 在錯誤頁面提供一鍵同步按鈕，免開終端機 */}
        <div className="glass-card" style={{
          padding: '1.5rem',
          borderRadius: '15px',
          border: '1px solid var(--border-color)',
          background: 'rgba(255,255,255,0.02)',
          marginBottom: '2rem',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1rem',
          width: '100%'
        }}>
          <h4 style={{ color: '#fff', fontSize: '0.9rem', fontWeight: 600 }}>您可以直接使用「一鍵同步雲端發票」功能來建立資料庫：</h4>
          
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>從</span>
              <input 
                type="date" 
                value={startDate} 
                onChange={(e) => setStartDate(e.target.value)}
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#fff',
                  borderRadius: '0.5rem',
                  padding: '0.35rem 0.5rem',
                  fontSize: '0.75rem',
                  outline: 'none'
                }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>到</span>
              <input 
                type="date" 
                value={endDate} 
                onChange={(e) => setEndDate(e.target.value)}
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#fff',
                  borderRadius: '0.5rem',
                  padding: '0.35rem 0.5rem',
                  fontSize: '0.75rem',
                  outline: 'none'
                }}
              />
            </div>
          </div>
          
          <button 
            onClick={handleRunCrawler}
            disabled={crawlerLoading}
            style={{
              background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
              border: 'none',
              color: '#fff',
              padding: '0.6rem 1.5rem',
              borderRadius: '0.75rem',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: crawlerLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
              transition: 'all 0.2s ease',
              marginTop: '0.5rem'
            }}
          >
            <RefreshCw size={16} className={crawlerLoading ? 'spin' : ''} />
            {crawlerLoading ? '正在同步雲端發票...' : '一鍵同步雲端發票'}
          </button>
        </div>
        
        {/* 全螢幕載入遮罩 */}
        {crawlerLoading && renderCrawlerLoadingOverlay()}
        
        {crawlerError && (
          <p style={{ color: '#ef4444', fontSize: '0.85rem', marginTop: '-1.5rem', marginBottom: '1.5rem' }}>
            ✕ 同步失敗：{crawlerError}
          </p>
        )}
        
        <button onClick={fetchInvoiceData} className="chart-btn active" style={{ padding: '0.6rem 1.5rem', borderRadius: '10px', background: 'none', border: '1px solid var(--border-color)' }}>
          重新整理試試看
        </button>
      </div>
    );
  }

  const { summary, trends, categories, topSellers, heatmap, invoices } = data;

  // ----------------------------------------------------
  // 發票搜尋、過濾與排序邏輯
  // ----------------------------------------------------
  const filteredInvoices = invoices.filter(inv => {
    // 關鍵字搜尋：搜尋店家、品項名稱、發票號碼
    const matchQuery = 
      inv.sellerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.invNum.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.items.some(item => item.itemName.toLowerCase().includes(searchQuery.toLowerCase()));
      
    // 類別過濾 (檢查發票內是否含有特定分類的品項，或發票主類別)
    const matchCategory = categoryFilter === 'All' || 
      inv.items.some(item => item.category === categoryFilter);
      
    // 狀態過濾
    const matchStatus = statusFilter === 'All' ||
      (statusFilter === 'Active' && inv.invStatus === '已開立') ||
(statusFilter === 'Voided' && inv.invStatus === '已作廢') ||
      (statusFilter === 'Refund' && inv.isRefund);
      
    return matchQuery && matchCategory && matchStatus;
  }).sort((a, b) => {
    // 排序邏輯
    if (sortBy === 'newest') {
      return new Date(`${a.date}T${a.invTime}`) < new Date(`${b.date}T${b.invTime}`) ? 1 : -1;
    } else if (sortBy === 'oldest') {
      return new Date(`${a.date}T${a.invTime}`) > new Date(`${b.date}T${b.invTime}`) ? 1 : -1;
    } else if (sortBy === 'highest') {
      return b.amount - a.amount;
    } else if (sortBy === 'lowest') {
      return a.amount - b.amount;
    }
    return 0;
  });

  // 計算熱力圖最大交易張數，用來換算相對透明度
  const maxHeatmapCount = heatmap.reduce((max, cell) => cell.count > max ? cell.count : max, 0);

  return (
    <div className="dashboard-wrapper">
      
      {/* 標題與更新區塊 */}
      <div className="dashboard-title-area">
        <div>
          <h1 className="dashboard-title">
            <Wallet size={36} style={{ color: 'var(--primary)' }} />
            財政部電子發票大數據儀表板
          </h1>
          <p className="dashboard-subtitle">
            基於 Python Pandas 清洗核心 • 本地發票庫區間：{summary.minDate ? `${summary.minDate.replace(/-/g, '/')} ~ ${summary.maxDate.replace(/-/g, '/')}` : '無資料'}
          </p>
        </div>
        {/* 新增：發票同步爬蟲控制台 */}
        <div className="glass-card crawler-panel" style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '1.25rem', 
          padding: '0.6rem 1.2rem', 
          borderRadius: '12px',
          border: '1px solid var(--border-color)',
          background: 'rgba(255,255,255,0.02)'
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>本地最近一筆日期</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Calendar size={14} style={{ color: 'var(--primary)' }} />
              <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#fff', fontFamily: 'Outfit, sans-serif' }}>
                {summary.maxDate ? summary.maxDate.replace(/-/g, '/') : '無資料'}
              </span>
            </div>
          </div>
          
          <div style={{ height: '24px', width: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
          
          <button 
            onClick={handleRunCrawler}
            disabled={crawlerLoading}
            style={{
              background: 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)',
              border: 'none',
              color: '#fff',
              padding: '0.6rem 1.2rem',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: crawlerLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              boxShadow: '0 4px 10px rgba(99, 102, 241, 0.2)',
              transition: 'all 0.2s ease'
            }}
          >
            <RefreshCw size={14} className={crawlerLoading ? 'spin' : ''} />
            {crawlerLoading ? '正在同步...' : '同步雲端發票'}
          </button>
        </div>
      </div>

      {/* KPI 卡片網格 */}
      <div className="kpi-grid">
        {/* KPI 1: 總消費 */}
        <div className="glass-card kpi-card">
          <div className="kpi-icon-container blue">
            <Wallet size={24} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">有效消費總額</span>
            <span className="kpi-value">{formatCurrency(summary.totalSpend)}</span>
            <span className="kpi-subtext">排除已作廢，抵消退貨後淨支出</span>
          </div>
        </div>

        {/* KPI 2: 發票張數 */}
        <div className="glass-card kpi-card">
          <div className="kpi-icon-container purple">
            <Receipt size={24} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">有效發票張數</span>
            <span className="kpi-value">{summary.totalInvoices} 張</span>
            <span className="kpi-subtext">已載入區間累計載具發票</span>
          </div>
        </div>

        {/* KPI 3: 平均每張花費 */}
        <div className="glass-card kpi-card">
          <div className="kpi-icon-container emerald">
            <TrendingUp size={24} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">每張平均消費額</span>
            <span className="kpi-value">{formatCurrency(summary.averageInvoiceSpend)}</span>
            <span className="kpi-subtext">單張發票平均客單價</span>
          </div>
        </div>

        {/* KPI 4: 異常/退貨作廢 */}
        <div 
          className="glass-card kpi-card clickable-kpi-card" 
          onClick={() => setShowRefundModal(true)}
          style={{ 
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-4px)';
            e.currentTarget.style.boxShadow = '0 12px 20px rgba(239, 68, 68, 0.15)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          <div className="kpi-icon-container crimson">
            <AlertTriangle size={24} />
          </div>
          <div className="kpi-content" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <span className="kpi-label">異常值處理統計</span>
              <span style={{ fontSize: '0.75rem', color: '#f87171', display: 'flex', alignItems: 'center', gap: '0.1rem', fontWeight: 600 }}>
                明細 <ArrowUpRight size={12} />
              </span>
            </div>
            <span className="kpi-value" style={{ fontSize: '1.25rem', marginTop: '0.35rem', fontWeight: 700, color: '#f87171' }}>
              退貨: {summary.totalRefundCount}筆 ({formatCurrency(Math.abs(summary.totalRefundAmount))})
            </span>
            <span className="kpi-subtext" style={{ color: '#cbd5e1' }}>
              作廢: {summary.voidedCount}張發票已完全剔除
            </span>
          </div>
        </div>
      </div>

      {/* 主圖表區塊 (趨勢線圖與類別圓餅圖) */}
      <div className="charts-grid-main">
        
        {/* 趨勢線圖 */}
        <div className="glass-card">
          <div className="chart-header">
            <h3 className="chart-title">
              <TrendingUp size={18} />
              消費趨勢分析線圖
            </h3>
            <div className="chart-actions">
              <button 
                onClick={() => setTrendMode('monthly')} 
                className={`chart-btn ${trendMode === 'monthly' ? 'active' : ''}`}
              >
                按月呈現
              </button>
              <button 
                onClick={() => setTrendMode('weekly')} 
                className={`chart-btn ${trendMode === 'weekly' ? 'active' : ''}`}
              >
                按週呈現 (近12週)
              </button>
            </div>
          </div>
          <div className="chart-container-inner">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={trendMode === 'monthly' ? trends.monthly : trends.weekly}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="var(--primary)" stopOpacity={0.0}/>
                  </linearGradient>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--secondary)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--secondary)" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  dataKey={trendMode === 'monthly' ? 'month' : 'week_label'} 
                  stroke="var(--text-secondary)"
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis 
                  yAxisId="left"
                  stroke="var(--text-secondary)"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(val) => `NT$${val}`}
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right"
                  stroke="var(--text-muted)"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(val) => `${val}張`}
                />
                <ChartTooltip 
                  contentStyle={{ 
                    background: '#0f172a', 
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: 'white',
                    fontSize: '12px'
                  }}
                  formatter={(value, name) => {
                    if (name === "消費總額") return [formatCurrency(value), name];
                    return [`${value} 張`, name];
                  }}
                />
                <Area 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="amount" 
                  name="消費總額" 
                  stroke="var(--primary)" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorAmount)" 
                />
                <Area 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="count" 
                  name="交易張數" 
                  stroke="var(--secondary)" 
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  fillOpacity={1} 
                  fill="url(#colorCount)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 類別圓餅圖 */}
        <div className="glass-card">
          <div className="chart-header">
            <h3 className="chart-title">
              <Info size={18} />
              各消費類別佔比
            </h3>
          </div>
          <div className="chart-container-inner" style={{ flexDirection: 'column', height: 'auto', minHeight: '320px', justifyContent: 'space-around' }}>
            <div style={{ width: '100%', height: '180px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categories}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="amount"
                    nameKey="category"
                  >
                    {categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[entry.category] || CATEGORY_COLORS['其它']} />
                    ))}
                  </Pie>
                  <ChartTooltip 
                    contentStyle={{ 
                      background: '#0f172a', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      color: 'white',
                      fontSize: '12px'
                    }}
                    formatter={(value) => [formatCurrency(value), "總花費"]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            {/* 圓餅圖圖例與比例數據 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', width: '100%', padding: '0.5rem' }}>
              {categories.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem' }}>
                  <div style={{ 
                    width: '10px', 
                    height: '10px', 
                    borderRadius: '50%', 
                    backgroundColor: CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它'] 
                  }}></div>
                  <span style={{ color: 'var(--text-secondary)', fontWeight: 500, flex: 1 }}>{item.category}</span>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{item.percentage}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 次級圖表區塊 (最愛店家與時段熱力圖) */}
      <div className="charts-grid-secondary">
        
        {/* 最愛店家 Top 10 */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="chart-header">
            <h3 className="chart-title">
              <Building size={18} />
              消費最高店家排行 Top 10
            </h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', flex: 1, alignItems: 'center' }}>
            {/* 左側長條圖 */}
            <div style={{ width: '100%', height: '260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={topSellers}
                  layout="vertical"
                  margin={{ top: 0, right: 0, left: -25, bottom: 0 }}
                >
                  <XAxis type="number" stroke="var(--text-muted)" fontSize={9} tickLine={false} />
                  <YAxis dataKey="sellerShort" type="category" stroke="var(--text-secondary)" fontSize={9} tickLine={false} width={45} />
                  <ChartTooltip 
                    contentStyle={{ 
                      background: '#0f172a', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      color: 'white',
                      fontSize: '12px'
                    }}
                    formatter={(value) => [formatCurrency(value), "消費額"]}
                  />
                  <Bar dataKey="amount" fill="url(#sellerBarGrad)" radius={[0, 4, 4, 0]}>
                    {topSellers.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={`url(#sellerBarGrad-${index % 2 === 0 ? '1' : '2'})`} />
                    ))}
                  </Bar>
                  <defs>
                    <linearGradient id="sellerBarGrad-1" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#6366f1" />
                      <stop offset="100%" stopColor="#4f46e5" />
                    </linearGradient>
                    <linearGradient id="sellerBarGrad-2" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#a855f7" />
                      <stop offset="100%" stopColor="#7c3aed" />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            </div>
            
            {/* 右側排行卡片清單 */}
            <div className="top-sellers-list">
              {topSellers.slice(0, 5).map((seller, idx) => (
                <div key={idx} className="seller-rank-row">
                  <div className="seller-rank-left">
                    <div className={`seller-rank-badge rank-${idx + 1}`}>
                      {idx + 1}
                    </div>
                    <span className="seller-rank-name">{seller.sellerShort}</span>
                  </div>
                  <div className="seller-rank-right">
                    <span className="seller-rank-amount">{formatCurrency(seller.amount)}</span>
                    <span className="seller-rank-count">{seller.count} 次交易</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 時段熱力圖 */}
        <div className="glass-card">
          <div className="chart-header">
            <h3 className="chart-title">
              <Calendar size={18} />
              特定時段消費熱力圖 (星期 vs 時段)
            </h3>
          </div>
          
          <div className="heatmap-container">
            <div className="heatmap-legend">
              <span>少交易</span>
              <div className="legend-bar"></div>
              <span>多交易</span>
            </div>
            
            <div className="heatmap-grid-scroll">
              <div className="heatmap-grid">
                {/* 頂部星期標頭 */}
                <div className="heatmap-header-cell">時段 \ 星期</div>
                <div className="heatmap-header-cell">週一</div>
                <div className="heatmap-header-cell">週二</div>
                <div className="heatmap-header-cell">週三</div>
                <div className="heatmap-header-cell">週四</div>
                <div className="heatmap-header-cell">週五</div>
                <div className="heatmap-header-cell">週六</div>
                <div className="heatmap-header-cell">週日</div>
                
                {/* 時段列渲染 */}
                {['早餐 (06-11)', '午餐 (11-14)', '下午茶 (14-17)', '晚餐 (17-21)', '深夜 (21-06)'].map((p, pIdx) => (
                  <React.Fragment key={pIdx}>
                    {/* 左側時段標籤 */}
                    <div className="heatmap-label-cell">
                      {p.split(' ')[0]}
                    </div>
                    
                    {/* 星期一至日各區塊 */}
                    {['週一', '週二', '週三', '週四', '週五', '週六', '週日'].map((w, wIdx) => {
                      const cell = heatmap.find(c => c.weekday === w && c.period === p) || { count: 0, amount: 0 };
                      
                      // 依據 count 計算熱力圖背景深淺度
                      const opacity = maxHeatmapCount > 0 ? (cell.count / maxHeatmapCount) * 0.8 + 0.15 : 0.06;
                      const hasData = cell.count > 0;
                      
                      return (
                        <div 
                          key={wIdx} 
                          className="heatmap-block"
                          style={{
                            backgroundColor: hasData ? `rgba(99, 102, 241, ${opacity})` : 'rgba(255, 255, 255, 0.02)',
                            color: hasData ? '#fff' : 'rgba(255, 255, 255, 0.15)',
                            border: hasData ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid rgba(255, 255, 255, 0.03)'
                          }}
                        >
                          {cell.count > 0 ? cell.count : ''}
                          
                          {/* 懸停工具提示 */}
                          <div className="heatmap-tooltip">
                            <div style={{ fontWeight: 700, marginBottom: '0.2rem' }}>{w} • {p.split(' ')[0]}</div>
                            <div>交易張數: {cell.count} 張</div>
                            <div>累計金額: {formatCurrency(cell.amount)}</div>
                          </div>
                        </div>
                      );
                    })}
                  </React.Fragment>
                ))}
              </div>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.5rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <Info size={12} />
                <span>格內數字代表交易發票張數，滑鼠移入格內可查看該時段累計消費總金額。</span>
              </div>
              <div style={{ fontSize: '0.72rem', color: '#fca5a5', display: 'flex', alignItems: 'center', gap: '0.25rem', opacity: 0.85 }}>
                <AlertTriangle size={12} style={{ color: '#ef4444' }} />
                <span>註：財政部官網匯出的載具 CSV 明細檔案「未包含交易時間」，因此匯入後系統預設時間為 12:00:00，故熱力圖會集中在午餐時段呈現（此為財政部原始資料之限制）。</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 發票明細與進階篩選 */}
      <div className="glass-card">
        <div className="chart-header" style={{ marginBottom: '1rem' }}>
          <h3 className="chart-title">
            <Receipt size={18} />
            雲端發票明細明細庫 ({filteredInvoices.length} 筆項目匹配)
          </h3>
        </div>

        {/* 篩選與搜尋面板 */}
        <div className="filters-area">
          {/* 搜尋框 */}
          <div className="search-input-wrapper">
            <Search size={18} />
            <input 
              type="text" 
              placeholder="搜尋店家名稱、商品品項或發票號碼..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>

          {/* 類別篩選 */}
          <select 
            value={categoryFilter} 
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="filter-select"
          >
            <option value="All">所有類別 (All)</option>
            <option value="飲食">飲食 (Food)</option>
            <option value="交通">交通 (Transport)</option>
            <option value="娛樂">娛樂 (Entertainment)</option>
            <option value="3C配件">3C配件 (Electronics)</option>
            <option value="服飾">服飾 (Clothing)</option>
            <option value="醫療">醫療 (Healthcare)</option>
            <option value="其它">其它 (Others)</option>
          </select>

          {/* 狀態篩選 */}
          <select 
            value={statusFilter} 
            onChange={(e) => setStatusFilter(e.target.value)}
            className="filter-select"
          >
            <option value="All">所有發票狀態</option>
            <option value="Active">正常有效發票</option>
            <option value="Voided">已作廢發票</option>
            <option value="Refund">退貨/退款項目</option>
          </select>

          {/* 排序規則 */}
          <select 
            value={sortBy} 
            onChange={(e) => setSortBy(e.target.value)}
            className="filter-select"
          >
            <option value="newest">時間排序：由新到舊</option>
            <option value="oldest">時間排序：由舊到新</option>
            <option value="highest">金額排序：由高到低</option>
            <option value="lowest">金額排序：由低到高</option>
          </select>
        </div>

        {/* 發票列表卡片 grid / Accordion */}
        <div className="invoices-list-container">
          {filteredInvoices.length === 0 ? (
            <div className="empty-state">
              <HelpCircle size={48} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
              <p>沒有找到符合篩選條件的發票項目</p>
            </div>
          ) : (
            filteredInvoices.map((inv, idx) => {
              const isExpanded = expandedInvoices[inv.invNum] || false;
              const isVoided = inv.invStatus === '已作廢';
              const isRefund = inv.isRefund;
              
              // 決定發票主導分類標記
              const primaryCategory = inv.items[0]?.category || '其它';
              
              return (
                <div 
                  key={inv.invNum} 
                  style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
                >
                  {/* 發票主列 */}
                  <div 
                    className="invoice-item-row"
                    onClick={() => toggleInvoiceExpand(inv.invNum)}
                    style={{ 
                      cursor: 'pointer',
                      borderLeft: isVoided 
                        ? '4px solid var(--danger)' 
                        : isRefund 
                          ? '4px solid var(--danger)' 
                          : `4px solid ${CATEGORY_COLORS[primaryCategory] || CATEGORY_COLORS['其它']}`,
                      opacity: isVoided ? 0.6 : 1
                    }}
                  >
                    <div className="invoice-left">
                      <div className="invoice-icon" style={{ color: CATEGORY_COLORS[primaryCategory] || CATEGORY_COLORS['其它'] }}>
                        <Receipt size={18} />
                      </div>
                      <div className="invoice-main-info">
                        <span className="invoice-seller">
                          {inv.sellerName}
                          {isVoided && <span style={{ color: 'var(--danger)', fontSize: '0.8rem', marginLeft: '0.5rem' }}>(已作廢)</span>}
                        </span>
                        <div className="invoice-meta">
                          <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{inv.invNum}</span>
                          <span>•</span>
                          <span>{inv.date} {inv.invTime} ({inv.weekday})</span>
                          <span>•</span>
                          <span className="invoice-badge-cat">{primaryCategory}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="invoice-right">
                      <span className={`invoice-amount-display ${isRefund ? 'refund' : 'normal'}`}>
                        {isRefund ? '-' : ''}{formatCurrency(Math.abs(inv.amount))}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>含 {inv.items.length} 項商品</span>
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </div>
                    </div>
                  </div>

                  {/* 展開的品項明細表格 */}
                  {isExpanded && (
                    <div style={{ 
                      background: 'rgba(255, 255, 255, 0.01)',
                      border: '1px solid rgba(255, 255, 255, 0.03)',
                      borderRadius: '12px',
                      padding: '1rem',
                      marginLeft: '0.25rem',
                      marginBottom: '0.5rem',
                      animation: 'fadeIn 0.2s ease'
                    }}>
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                          <thead>
                            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                              <th style={{ padding: '0.5rem 0.5rem 0.5rem 0' }}>品項描述</th>
                              <th style={{ padding: '0.5rem', textAlign: 'center' }}>數量</th>
                              <th style={{ padding: '0.5rem', textAlign: 'right' }}>單價</th>
                              <th style={{ padding: '0.5rem', textAlign: 'right' }}>金額</th>
                              <th style={{ padding: '0.5rem 0 0.5rem 0.5rem', textAlign: 'center' }}>自動分類</th>
                            </tr>
                          </thead>
                          <tbody>
                            {inv.items.map((item, itemIdx) => (
                              <tr key={itemIdx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                                <td style={{ padding: '0.65rem 0.5rem 0.65rem 0', fontWeight: 500, color: 'var(--text-primary)' }}>
                                  {item.itemName}
                                </td>
                                <td style={{ padding: '0.65rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                  {item.qty}
                                </td>
                                <td style={{ padding: '0.65rem', textAlign: 'right', color: 'var(--text-secondary)' }}>
                                  {formatCurrency(item.price)}
                                </td>
                                <td style={{ padding: '0.65rem', textAlign: 'right', fontWeight: 600, color: item.amount < 0 ? 'var(--danger)' : 'var(--text-primary)' }}>
                                  {formatCurrency(item.amount)}
                                </td>
                                <td style={{ padding: '0.65rem 0 0.65rem 0.5rem', textAlign: 'center' }}>
                                  <span style={{ 
                                    padding: '0.15rem 0.45rem', 
                                    borderRadius: '4px',
                                    fontSize: '0.65rem',
                                    fontWeight: 600,
                                    backgroundColor: `${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']}15`,
                                    color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它'],
                                    border: `1px solid ${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']}25`
                                  }}>
                                    {item.category}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
      
      {/* 退貨明細彈出視窗 (Refund Details Modal) */}
      {showRefundModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.8)',
          backdropFilter: 'blur(12px)',
          zIndex: 99999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem',
          animation: 'fadeIn 0.25s ease'
        }}>
          <div className="glass-card" style={{
            maxWidth: '850px',
            width: '100%',
            maxHeight: '85vh',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            background: 'rgba(30, 41, 59, 0.7)',
            overflow: 'hidden'
          }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div className="kpi-icon-container crimson" style={{ width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '10px' }}>
                  <AlertTriangle size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>退貨明細清單</h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    本地發票庫累計退貨：{summary.totalRefundCount} 筆，金額：{formatCurrency(Math.abs(summary.totalRefundAmount))}
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setShowRefundModal(false)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: 'none',
                  color: '#fff',
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: 'bold',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.target.style.background = 'rgba(239, 68, 68, 0.2)'}
                onMouseLeave={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.05)'}
              >
                ✕
              </button>
            </div>

            {/* Modal Content - Refund Invoices Scroll Area */}
            <div style={{ overflowY: 'auto', flex: 1, paddingRight: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {invoices.filter(inv => inv.isRefund).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  <HelpCircle size={48} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                  <p>目前本地發票庫中查無退貨記錄</p>
                </div>
              ) : (
                invoices.filter(inv => inv.isRefund).map((inv) => {
                  const isExpanded = expandedRefundInvoices[inv.invNum] || false;
                  const primaryCategory = inv.items[0]?.category || '其它';
                  
                  return (
                    <div key={inv.invNum} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <div 
                        className="invoice-item-row"
                        onClick={() => setExpandedRefundInvoices(prev => ({ ...prev, [inv.invNum]: !prev[inv.invNum] }))}
                        style={{ 
                          cursor: 'pointer',
                          borderLeft: '4px solid var(--danger)',
                          background: 'rgba(255, 255, 255, 0.02)',
                          width: '100%',
                          display: 'flex',
                          justifyContent: 'space-between',
                          padding: '1rem',
                          borderRadius: '8px',
                          border: '1px solid rgba(255, 255, 255, 0.05)',
                          alignItems: 'center'
                        }}
                      >
                        <div className="invoice-left" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <div className="invoice-icon" style={{ color: 'var(--danger)' }}>
                            <Receipt size={18} />
                          </div>
                          <div className="invoice-main-info" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span className="invoice-seller" style={{ color: '#fff', fontWeight: 600, fontSize: '0.9rem' }}>{inv.sellerName}</span>
                            <div className="invoice-meta" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{inv.invNum}</span>
                              <span>•</span>
                              <span>{inv.date} {inv.invTime} ({inv.weekday})</span>
                              <span>•</span>
                              <span className="invoice-badge-cat" style={{ borderColor: 'rgba(239, 68, 68, 0.3)', color: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.08)' }}>
                                {primaryCategory}
                              </span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="invoice-right" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                          <span className="invoice-amount-display refund" style={{ color: 'var(--danger)', fontWeight: 700, fontSize: '1.1rem' }}>
                            {formatCurrency(inv.items.filter(item => item.amount < 0).reduce((sum, item) => sum + item.amount, 0))}
                          </span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            <span>含 {inv.items.filter(item => item.amount < 0).length} 項退貨品項</span>
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </div>
                        </div>
                      </div>

                      {/* Expandable refund items table */}
                      {isExpanded && (
                        <div style={{ 
                          background: 'rgba(239, 68, 68, 0.02)',
                          border: '1px solid rgba(239, 68, 68, 0.05)',
                          borderRadius: '12px',
                          padding: '1rem',
                          marginLeft: '0.25rem',
                          marginBottom: '0.5rem',
                          animation: 'fadeIn 0.2s ease'
                        }}>
                          <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                              <thead>
                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                                  <th style={{ padding: '0.5rem 0.5rem 0.5rem 0' }}>退貨品項</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'center' }}>數量</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>單價</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>退款金額</th>
                                  <th style={{ padding: '0.5rem 0 0.5rem 0.5rem', textAlign: 'center' }}>分類</th>
                                </tr>
                              </thead>
                              <tbody>
                                {inv.items.filter(item => item.amount < 0).map((item, itemIdx) => (
                                  <tr key={itemIdx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                                    <td style={{ padding: '0.65rem 0.5rem 0.65rem 0', fontWeight: 500, color: 'var(--text-primary)' }}>
                                      {item.itemName}
                                    </td>
                                    <td style={{ padding: '0.65rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                      {item.qty}
                                    </td>
                                    <td style={{ padding: '0.65rem', textAlign: 'right', color: 'var(--text-secondary)' }}>
                                      {formatCurrency(item.price)}
                                    </td>
                                    <td style={{ padding: '0.65rem', textAlign: 'right', fontWeight: 600, color: 'var(--danger)' }}>
                                      {formatCurrency(item.amount)}
                                    </td>
                                    <td style={{ padding: '0.65rem 0 0.65rem 0.5rem', textAlign: 'center' }}>
                                      <span style={{ 
                                        padding: '0.15rem 0.45rem', 
                                        borderRadius: '4px',
                                        fontSize: '0.65rem',
                                        fontWeight: 600,
                                        backgroundColor: `${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']}15`,
                                        color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它'],
                                        border: `1px solid ${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']}25`
                                      }}>
                                        {item.category}
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Modal Footer */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '1rem' }}>
              <button 
                onClick={() => setShowRefundModal(false)}
                className="chart-btn active"
                style={{ padding: '0.5rem 1.5rem', borderRadius: '8px' }}
              >
                關閉視窗
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 底部導引說明 */}
      <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
        臺灣財政部電子發票自動介接系統庫 • 專案連結：<a href="https://github.com/futeeeen/personal-finance-review.git" target="_blank" style={{ color: 'var(--primary)' }}>personal-finance-review</a>
      </div>
    </div>
  );
}

export default App;
