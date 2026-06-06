import React, { useState, useEffect, useMemo } from 'react';
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
  HelpCircle,
  Palette,
  CalendarRange,
  Sparkles
} from 'lucide-react';

// 定義分類的色彩映射 (對應 CSS 變數，支援風格切換時即時變色)
const CATEGORY_COLORS = {
  '飲食': 'var(--cat-food)',
  '交通': 'var(--cat-trans)',
  '娛樂': 'var(--cat-ent)',
  '3C配件': 'var(--cat-electronics)',
  '服飾': 'var(--cat-cloth)',
  '醫療': 'var(--cat-med)',
  '其它': 'var(--cat-other)'
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

// 輔助函式：計算給定日期的 ISO 週別 (1~53)
const getISOWeekNumber = (dateStr) => {
  const d = new Date(dateStr);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + 4 - (d.getDay() || 7));
  const yearStart = new Date(d.getFullYear(), 0, 1);
  const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  return weekNo;
};

const themes = [
  { id: 'glass-dark', name: '深藍磨砂', color: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)' },
  { id: 'cyberpunk', name: '霓虹賽博', color: 'linear-gradient(135deg, #00f0ff 0%, #ff007f 100%)' },
  { id: 'emerald-light', name: '極簡森林', color: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)' },
  { id: 'sunset-aurora', name: '暮色極光', color: 'linear-gradient(135deg, #f43f5e 0%, #fb923c 100%)' }
];

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 主題風格狀態
  const [activeTheme, setActiveTheme] = useState(() => {
    return localStorage.getItem('finance-dashboard-theme') || 'glass-dark';
  });

  useEffect(() => {
    const body = document.body;
    body.className = '';
    body.classList.add(`theme-${activeTheme}`);
    localStorage.setItem('finance-dashboard-theme', activeTheme);
  }, [activeTheme]);
  
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
  const [crawlerStatusMessage, setCrawlerStatusMessage] = useState('準備就緒');
  const [crawlerStatusStep, setCrawlerStatusStep] = useState('idle');
  
  // 退貨明細彈出視窗狀態
  const [showRefundModal, setShowRefundModal] = useState(false);
  const [expandedRefundInvoices, setExpandedRefundInvoices] = useState({});
  
  // 分類明細彈出視窗狀態
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [expandedCategoryInvoices, setExpandedCategoryInvoices] = useState({});
  
  const handleCategoryClick = (categoryName) => {
    setSelectedCategory(categoryName);
    setShowCategoryModal(true);
    setExpandedCategoryInvoices({});
  };

  // 店家明細彈出視窗狀態
  const [showSellerModal, setShowSellerModal] = useState(false);
  const [selectedSeller, setSelectedSeller] = useState('');
  const [expandedSellerInvoices, setExpandedSellerInvoices] = useState({});
  
  // 儀表板時間區間過濾狀態
  const [filterStartDate, setFilterStartDate] = useState('');
  const [filterEndDate, setFilterEndDate] = useState('');

  // ----------------------------------------------------
  // 自訂日曆控制與輔助邏輯 (100% 點擊式操作，解決原生土味與輸入困擾)
  // ----------------------------------------------------
  const [showStartCalendar, setShowStartCalendar] = useState(false);
  const [showEndCalendar, setShowEndCalendar] = useState(false);
  const [startCalView, setStartCalView] = useState({ year: 2025, month: 8 });
  const [endCalView, setEndCalView] = useState({ year: 2026, month: 4 });

  useEffect(() => {
    if (data?.summary) {
      setFilterStartDate(data.summary.minDate || '');
      setFilterEndDate(data.summary.maxDate || '');
      
      if (data.summary.minDate) {
        const [y, m] = data.summary.minDate.split('-').map(Number);
        setStartCalView({ year: y, month: m - 1 });
      }
      if (data.summary.maxDate) {
        const [y, m] = data.summary.maxDate.split('-').map(Number);
        setEndCalView({ year: y, month: m - 1 });
      }
    }
  }, [data]);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (!e.target.closest('.custom-calendar-container')) {
        setShowStartCalendar(false);
        setShowEndCalendar(false);
      }
    };
    document.addEventListener('click', handleOutsideClick);
    return () => document.removeEventListener('click', handleOutsideClick);
  }, []);

  const getCalendarDays = (year, month) => {
    const firstDay = new Date(year, month, 1);
    const dayOfWeek = firstDay.getDay();
    const startDayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1;

    const totalDaysCurr = new Date(year, month + 1, 0).getDate();
    const totalDaysPrev = new Date(year, month, 0).getDate();

    const cells = [];

    const prevMonth = month === 0 ? 11 : month - 1;
    const prevYear = month === 0 ? year - 1 : year;
    for (let i = startDayOffset - 1; i >= 0; i--) {
      const d = totalDaysPrev - i;
      cells.push({
        day: d,
        month: prevMonth,
        year: prevYear,
        isCurrentMonth: false,
        dateStr: `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      });
    }

    for (let d = 1; d <= totalDaysCurr; d++) {
      cells.push({
        day: d,
        month: month,
        year: year,
        isCurrentMonth: true,
        dateStr: `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      });
    }

    const nextMonth = month === 11 ? 0 : month + 1;
    const nextYear = month === 11 ? year + 1 : year;
    const remaining = 42 - cells.length;
    for (let d = 1; d <= remaining; d++) {
      cells.push({
        day: d,
        month: nextMonth,
        year: nextYear,
        isCurrentMonth: false,
        dateStr: `${nextYear}-${String(nextMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      });
    }

    return cells;
  };

  const handlePrevMonth = (type) => {
    if (type === 'start') {
      setStartCalView(prev => {
        const nextMonth = prev.month === 0 ? 11 : prev.month - 1;
        const nextYear = prev.month === 0 ? prev.year - 1 : prev.year;
        return { year: nextYear, month: nextMonth };
      });
    } else {
      setEndCalView(prev => {
        const nextMonth = prev.month === 0 ? 11 : prev.month - 1;
        const nextYear = prev.month === 0 ? prev.year - 1 : prev.year;
        return { year: nextYear, month: nextMonth };
      });
    }
  };

  const handleNextMonth = (type) => {
    if (type === 'start') {
      setStartCalView(prev => {
        const nextMonth = prev.month === 11 ? 0 : prev.month + 1;
        const nextYear = prev.month === 11 ? prev.year + 1 : prev.year;
        return { year: nextYear, month: nextMonth };
      });
    } else {
      setEndCalView(prev => {
        const nextMonth = prev.month === 11 ? 0 : prev.month + 1;
        const nextYear = prev.month === 11 ? prev.year + 1 : prev.year;
        return { year: nextYear, month: nextMonth };
      });
    }
  };

  const renderCustomCalendar = (type) => {
    const isStart = type === 'start';
    const currentView = isStart ? startCalView : endCalView;
    const selectedDate = isStart ? filterStartDate : filterEndDate;
    
    const days = getCalendarDays(currentView.year, currentView.month);
    const monthsName = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];

    const minDateLimit = isStart 
      ? (data?.summary?.minDate || '') 
      : (filterStartDate || data?.summary?.minDate || '');
    const maxDateLimit = isStart 
      ? (filterEndDate || data?.summary?.maxDate || '') 
      : (data?.summary?.maxDate || '');

    const handleDayClick = (dateStr) => {
      if (isStart) {
        setFilterStartDate(dateStr);
        setShowStartCalendar(false);
      } else {
        setFilterEndDate(dateStr);
        setShowEndCalendar(false);
      }
    };

    return (
      <div 
        className="glass-card" 
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute',
          top: '100%',
          [isStart ? 'left' : 'right']: 0,
          marginTop: '0.6rem',
          zIndex: 1000,
          width: '280px',
          padding: '1rem',
          borderRadius: '16px',
          border: '1px solid var(--border-color)',
          background: 'var(--bg-card)',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.35)',
          animation: 'calFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <button 
            onClick={() => handlePrevMonth(type)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              padding: '0.25rem 0.5rem',
              borderRadius: '6px',
              fontSize: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
          >
            &lt;
          </button>
          
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', gap: '0.25rem' }}>
            <span>{currentView.year} 年</span>
            <span>{monthsName[currentView.month]}</span>
          </div>

          <button 
            onClick={() => handleNextMonth(type)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              padding: '0.25rem 0.5rem',
              borderRadius: '6px',
              fontSize: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
          >
            &gt;
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '0.2rem', textAlign: 'center', marginBottom: '0.5rem' }}>
          {['一', '二', '三', '四', '五', '六', '日'].map(w => (
            <span key={w} style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)' }}>{w}</span>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '0.2rem' }}>
          {days.map((cell, idx) => {
            const isToday = cell.dateStr === getTodayStr();
            const isSelected = cell.dateStr === selectedDate;
            
            const isBeforeMin = minDateLimit && cell.dateStr < minDateLimit;
            const isAfterMax = maxDateLimit && cell.dateStr > maxDateLimit;
            const isDisabled = isBeforeMin || isAfterMax;

            const buttonStyle = {
              background: isSelected 
                ? 'linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)' 
                : 'none',
              border: isToday && !isSelected ? '1px solid var(--primary)' : 'none',
              color: isSelected 
                ? '#fff' 
                : isDisabled 
                  ? 'rgba(255,255,255,0.1)' 
                  : cell.isCurrentMonth 
                    ? 'var(--text-primary)' 
                    : 'var(--text-muted)',
              opacity: isDisabled ? 0.25 : cell.isCurrentMonth ? 1 : 0.5,
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.75rem',
              fontWeight: isSelected || isToday ? 'bold' : 'normal',
              padding: 0,
              outline: 'none',
              transition: 'all 0.15s ease',
              boxShadow: isSelected ? '0 0 6px var(--primary)' : 'none'
            };

            return (
              <button
                key={idx}
                disabled={isDisabled}
                onClick={() => handleDayClick(cell.dateStr)}
                style={buttonStyle}
                onMouseEnter={(e) => {
                  if (!isDisabled && !isSelected) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isDisabled && !isSelected) {
                    e.currentTarget.style.background = 'none';
                    e.currentTarget.style.color = cell.isCurrentMonth ? 'var(--text-primary)' : 'var(--text-muted)';
                  }
                }}
              >
                {cell.day}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  // 根據日期區間過濾後的基礎發票資料
  const activeInvoicesFiltered = useMemo(() => {
    if (!data || !data.invoices) return [];
    return data.invoices.filter(inv => {
      if (!filterStartDate && !filterEndDate) return true;
      if (filterStartDate && inv.date < filterStartDate) return false;
      if (filterEndDate && inv.date > filterEndDate) return false;
      return true;
    });
  }, [data, filterStartDate, filterEndDate]);

  const derivedData = useMemo(() => {
    if (!data || !data.invoices) return null;

    const invoicesFiltered = activeInvoicesFiltered;
    const df_active = invoicesFiltered.filter(inv => inv.invStatus !== '已作廢');
    const df_voided = invoicesFiltered.filter(inv => inv.invStatus === '已作廢');

    // 1. Spend
    const totalSpend = df_active.reduce((sum, inv) => sum + inv.amount, 0);
    const totalInvoices = df_active.length;
    const averageInvoiceSpend = totalInvoices > 0 ? Math.round(totalSpend / totalInvoices) : 0;

    // 2. Refunds
    let totalRefundAmount = 0;
    let totalRefundCount = 0;
    df_active.forEach(inv => {
      let hasRefundItem = false;
      inv.items.forEach(item => {
        if (item.amount < 0) {
          totalRefundAmount += item.amount;
          hasRefundItem = true;
        }
      });
      if (hasRefundItem) {
        totalRefundCount += 1;
      }
    });

    // 3. Voided
    const voidedCount = df_voided.length;
    const voidedAmount = df_voided.reduce((sum, inv) => sum + inv.amount, 0);

    const minDate = df_active.length > 0 
      ? df_active.reduce((min, inv) => inv.date < min ? inv.date : min, df_active[0].date) 
      : '';
    const maxDate = df_active.length > 0 
      ? df_active.reduce((max, inv) => inv.date > max ? inv.date : max, df_active[0].date) 
      : '';

    // 4. A. Month Trend
    const monthGroups = {};
    df_active.forEach(inv => {
      const m = inv.month || inv.date.substring(0, 7);
      if (!monthGroups[m]) {
        monthGroups[m] = { month: m, amount: 0, countSet: new Set() };
      }
      monthGroups[m].amount += inv.amount;
      monthGroups[m].countSet.add(inv.invNum);
    });
    const monthlyTrend = Object.values(monthGroups).map(g => ({
      month: g.month,
      amount: g.amount,
      count: g.countSet.size
    })).sort((a, b) => a.month.localeCompare(b.month));

    // B. Week Trend
    const weekGroups = {};
    df_active.forEach(inv => {
      const y = inv.year || new Date(inv.date).getFullYear();
      const w = inv.week_num || getISOWeekNumber(inv.date);
      const key = `${y}-W${w}`;
      if (!weekGroups[key]) {
        weekGroups[key] = { year: y, week_num: w, amount: 0, countSet: new Set() };
      }
      weekGroups[key].amount += inv.amount;
      weekGroups[key].countSet.add(inv.invNum);
    });
    const weeklyTrend = Object.values(weekGroups).map(g => ({
      week_label: `第 ${g.week_num} 週`,
      amount: g.amount,
      count: g.countSet.size,
      sortKey: `${g.year}-${String(g.week_num).padStart(2, '0')}`
    })).sort((a, b) => a.sortKey.localeCompare(b.sortKey)).slice(-12);

    // C. Categories (exclude negative values)
    const categoryGroups = {};
    df_active.forEach(inv => {
      inv.items.forEach(item => {
        if (item.amount > 0) {
          const cat = item.category || '其它';
          if (!categoryGroups[cat]) {
            categoryGroups[cat] = { category: cat, amount: 0, countSet: new Set() };
          }
          categoryGroups[cat].amount += item.amount;
          categoryGroups[cat].countSet.add(inv.invNum);
        }
      });
    });
    const categorySum = Object.values(categoryGroups).reduce((sum, g) => sum + g.amount, 0);
    const categoriesList = Object.values(categoryGroups).map(g => ({
      category: g.category,
      amount: g.amount,
      count: g.countSet.size,
      percentage: categorySum > 0 ? parseFloat((g.amount / categorySum * 100).toFixed(1)) : 0
    })).sort((a, b) => b.amount - a.amount);

    // D. Top Sellers
    const sellerGroups = {};
    df_active.forEach(inv => {
      if (inv.amount > 0) {
        const s = inv.sellerName;
        if (!sellerGroups[s]) {
          sellerGroups[s] = { sellerName: s, amount: 0, countSet: new Set() };
        }
        sellerGroups[s].amount += inv.amount;
        sellerGroups[s].countSet.add(inv.invNum);
      }
    });
    const topSellers = Object.values(sellerGroups).map(g => ({
      sellerName: g.sellerName,
      amount: g.amount,
      count: g.countSet.size
    })).sort((a, b) => b.amount - a.amount).slice(0, 10);

    return {
      summary: {
        totalSpend,
        totalInvoices,
        averageInvoiceSpend,
        totalRefundAmount,
        totalRefundCount,
        voidedCount,
        voidedAmount,
        minDate,
        maxDate,
        lastUpdated: data.summary?.lastUpdated || ''
      },
      trends: {
        monthly: monthlyTrend,
        weekly: weeklyTrend
      },
      categories: categoriesList,
      topSellers,
      invoices: invoicesFiltered
    };
  }, [data, activeInvoicesFiltered]);

  // 解構 derivedData，若為空則使用安全預設值，避免 data 為空時崩潰
  const { summary, trends, categories, topSellers, invoices } = derivedData || {
    summary: {},
    trends: { monthly: [], weekly: [] },
    categories: [],
    topSellers: [],
    invoices: []
  };

  const handleSellerClick = (sellerName) => {
    setSelectedSeller(sellerName);
    setShowSellerModal(true);
    setExpandedSellerInvoices({});
  };
  
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
    // 往回推 7 個月，並將日期設為該月第一天，動態計算 8 個月查詢上限，避免硬編碼
    const targetDate = new Date(d.getFullYear(), d.getMonth() - 7, 1);
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
      if (response.status === 404) {
        throw new Error('FIRST_TIME_USE');
      } else if (!response.ok) {
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
    setCrawlerStatusMessage('正在發送啟動請求...');
    setCrawlerStatusStep('init');
    
    let intervalId = null;

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
        let errMsg = '同步請求失敗，請確認伺服器是否正常運行！';
        try {
          const errJson = await response.json();
          if (errJson && errJson.message) {
            errMsg = errJson.message;
          }
        } catch (e) {}
        throw new Error(errMsg);
      }
      
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.message || '無法啟動同步任務');
      }

      setCrawlerStatusMessage('同步任務已啟動，正在初始化...');
      
      // 啟動成功，開始輪詢狀態
      intervalId = setInterval(async () => {
        try {
          const statusRes = await fetch('/api/crawler-status');
          if (!statusRes.ok) return;
          const statusData = await statusRes.json();
          
          setCrawlerStatusMessage(statusData.message || '進行中...');
          setCrawlerStatusStep(statusData.step || statusData.status || 'running');

          if (statusData.status === 'success') {
            clearInterval(intervalId);
            setCrawlerSuccess(true);
            setCrawlerLoading(false);
            await fetchInvoiceData();
          } else if (statusData.status === 'error') {
            clearInterval(intervalId);
            setCrawlerError(statusData.message || '自動化更新失敗。');
            setCrawlerStatusStep('error');
          }
        } catch (pollErr) {
          console.error('輪詢狀態出錯:', pollErr);
        }
      }, 1000);

    } catch (err) {
      console.error(err);
      setCrawlerError(err.message);
      setCrawlerStatusStep('error');
      setCrawlerStatusMessage(err.message);
      if (intervalId) clearInterval(intervalId);
    }
  };

  const renderProgressSteps = (currentStep) => {
    const steps = [
      { id: 'browser', label: '啟動瀏覽器並載入登入網頁', activeSteps: ['init', 'browser_started', 'loading_login'] },
      { id: 'captcha', label: '輸入圖形驗證碼並登入 (需手動)', activeSteps: ['captcha', 'waiting_captcha'] },
      { id: 'download', label: '大平台批次下載發票明細', activeSteps: ['login_success', 'downloading'] },
      { id: 'cleaning', label: 'Pandas 資料清洗與財務分析', activeSteps: ['cleaning'] },
      { id: 'done', label: '同步完成！', activeSteps: ['done', 'success'] }
    ];

    // 找出當前處於哪一個步驟
    let currentIdx = -1;
    for (let i = 0; i < steps.length; i++) {
      if (steps[i].activeSteps.includes(currentStep)) {
        currentIdx = i;
        break;
      }
    }

    // 如果發生錯誤，根據訊息猜測是在哪個步驟失敗
    if (currentStep === 'error') {
      if (crawlerStatusMessage.includes('清洗') || crawlerStatusMessage.includes('分析')) {
        currentIdx = 3;
      } else if (crawlerStatusMessage.includes('下載') || crawlerStatusMessage.includes('CSV')) {
        currentIdx = 2;
      } else if (crawlerStatusMessage.includes('登入') || crawlerStatusMessage.includes('驗證碼') || crawlerStatusMessage.includes('接管')) {
        currentIdx = 1;
      } else {
        currentIdx = 0;
      }
    }

    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.8rem',
        width: '100%',
        textAlign: 'left',
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        borderRadius: '12px',
        padding: '1.2rem',
        marginTop: '0.2rem',
        marginBottom: '0.2rem',
        boxSizing: 'border-box'
      }}>
        {steps.map((step, idx) => {
          const isCompleted = currentStep === 'done' || currentStep === 'success' || (currentIdx > idx && currentStep !== 'error');
          const isActive = currentIdx === idx && currentStep !== 'error';
          const isFailed = currentStep === 'error' && currentIdx === idx;
          
          let icon = (
            <div style={{
              width: '18px',
              height: '18px',
              borderRadius: '50%',
              border: '2px solid rgba(255, 255, 255, 0.15)',
              display: 'inline-block',
              boxSizing: 'border-box'
            }}></div>
          );
          let color = 'var(--text-muted)';
          let fontWeight = '400';

          if (isCompleted) {
            icon = (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'block' }}>
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            );
            color = 'rgba(255, 255, 255, 0.85)';
            fontWeight = '500';
          } else if (isActive) {
            icon = (
              <div className="spin" style={{
                width: '18px',
                height: '18px',
                borderRadius: '50%',
                border: '2px solid var(--primary)',
                borderTopColor: 'transparent',
                boxSizing: 'border-box',
                display: 'block'
              }}></div>
            );
            color = 'var(--primary)';
            fontWeight = '600';
          } else if (isFailed) {
            icon = (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'block' }}>
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            );
            color = 'var(--danger)';
            fontWeight = '600';
          }

          return (
            <div key={step.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.9rem', color }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '20px', height: '20px' }}>
                {icon}
              </div>
              <span style={{ transition: 'all 0.3s ease' }}>{step.label}</span>
            </div>
          );
        })}
      </div>
    );
  };

  const renderCrawlerLoadingOverlay = () => {
    const isError = crawlerStatusStep === 'error';
    const isCaptcha = crawlerStatusStep === 'captcha' || crawlerStatusStep === 'waiting_captcha';
    
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        backdropFilter: 'blur(12px)',
        zIndex: 99999,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        color: 'var(--text-primary)'
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
          boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)',
          border: '1px solid var(--border-color)',
          background: 'var(--bg-card)'
        }}>
          <div className={`kpi-icon-container ${isError ? 'red' : 'blue'}`} style={{ width: '64px', height: '64px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {isError ? (
              <ShieldAlert size={32} style={{ color: 'var(--danger)' }} />
            ) : (
              <RefreshCw size={32} className={isCaptcha ? "" : "spin"} />
            )}
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
              {isError ? '自動同步失敗' : '機器人正在自動同步發票...'}
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>查詢區間：{startDate} ~ {endDate}</p>
          </div>
          
          {/* 警告彈窗區：如果需要手動接管輸入驗證碼 */}
          {isCaptcha && (
            <div style={{
              background: 'rgba(234, 179, 8, 0.12)',
              border: '1px solid rgba(234, 179, 8, 0.5)',
              borderRadius: '12px',
              padding: '1rem',
              color: '#eab308',
              fontSize: '0.85rem',
              fontWeight: 600,
              width: '100%',
              textAlign: 'center',
              boxShadow: '0 0 10px rgba(234, 179, 8, 0.15)',
              lineHeight: '1.5'
            }}>
              ⚠️ 需要手動接管：請點選開啟的瀏覽器視窗，輸入圖形驗證碼並手動點擊「登入」！機器人在登入成功後將會自動繼續下載。
            </div>
          )}

          {/* 步驟指示器 */}
          {renderProgressSteps(crawlerStatusStep)}

          {/* 即時進度顯示 */}
          <div style={{
            background: 'var(--bg-item)',
            border: '1px solid var(--border-item)',
            borderRadius: '0.75rem',
            padding: '1rem',
            width: '100%',
            textAlign: 'left',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: isError ? 'var(--danger)' : (isCaptcha ? '#eab308' : 'var(--primary)'),
                boxShadow: isError ? '0 0 6px var(--danger)' : (isCaptcha ? '0 0 6px #eab308' : '0 0 6px var(--primary)')
              }}></span>
              <span style={{ fontWeight: 'bold' }}>目前進度:</span>
              <span>{crawlerStatusMessage}</span>
            </div>
          </div>
          
          {isError ? (
            <button
              onClick={() => {
                setCrawlerLoading(false);
                setCrawlerError(null);
              }}
              style={{
                background: 'linear-gradient(135deg, var(--danger) 0%, #be123c 100%)',
                border: 'none',
                color: '#fff',
                padding: '0.6rem 1.5rem',
                borderRadius: '0.75rem',
                fontSize: '0.9rem',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(239, 68, 68, 0.2)',
                transition: 'all 0.2s ease',
                width: '100%'
              }}
            >
              關閉視窗
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)', alignItems: 'center' }}>
              <Info size={14} />
              <span>請勿關閉網頁。同步發票可能需要 10~60 秒。</span>
            </div>
          )}
        </div>
      </div>
    );
  };

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
    const isFirstTime = error === 'FIRST_TIME_USE' || !error;
    return (
      <div className="loading-wrapper" style={{ padding: '3rem', textAlign: 'center', maxWidth: '600px', margin: '100px auto' }}>
        {isFirstTime ? (
          <Sparkles size={64} style={{ color: 'var(--primary)', marginBottom: '1rem' }} />
        ) : (
          <ShieldAlert size={64} style={{ color: 'var(--danger)', marginBottom: '1rem' }} />
        )}
        <h2 style={{ fontFamily: 'Outfit, sans-serif', marginBottom: '1rem', color: 'var(--text-primary)' }}>
          {isFirstTime ? '歡迎使用個人發票財務儀表板' : '載入發票數據失敗'}
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '2rem', lineHeight: '1.6' }}>
          {isFirstTime 
            ? '感謝您的使用！目前尚未匯入任何發票資料。請點擊下方的「一鍵同步雲端發票」按鈕開始取得您的真實發票，或者您也可以在 user_data/config.json 中填寫載具帳密以啟用自動登入。'
            : error
          }
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
          <h4 style={{ color: 'var(--text-primary)', fontSize: '0.9rem', fontWeight: 600 }}>您可以直接使用「一鍵同步雲端發票」功能來建立資料庫：</h4>
          
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

  // 星期熱力圖定義與聚合資料
  const heatmapCategories = ['飲食', '交通', '娛樂', '3C配件', '服飾', '醫療', '其它', '合計'];
  const weekdays = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
  
  // 動態計算 分類 vs 星期 2D 熱力圖格點資料
  const weekdayCategoryCells = [];
  heatmapCategories.forEach(cat => {
    weekdays.forEach(day => {
      const matches = invoices.filter(inv => {
        const isMatchDay = inv.weekday === day;
        if (cat === '合計') {
          return isMatchDay && inv.invStatus !== '已作廢';
        } else {
          const primaryCategory = inv.items[0]?.category || '其它';
          return isMatchDay && primaryCategory === cat && inv.invStatus !== '已作廢';
        }
      });
      
      weekdayCategoryCells.push({
        category: cat,
        weekday: day,
        count: matches.length,
        amount: matches.reduce((sum, inv) => sum + inv.amount, 0)
      });
    });
  });

  const maxCategoryCellCount = weekdayCategoryCells
    .filter(cell => cell.category !== '合計')
    .reduce((max, cell) => cell.count > max ? cell.count : max, 0);

  const maxTotalCellCount = weekdayCategoryCells
    .filter(cell => cell.category === '合計')
    .reduce((max, cell) => cell.count > max ? cell.count : max, 0);

  return (
    <div className="dashboard-wrapper">
      
      <style>{`
        @keyframes calFadeIn {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* 標題與更新區塊 */}
      <div className="dashboard-title-area" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.5rem' }}>
        <div>
          <h1 className="dashboard-title">
            <Wallet size={36} style={{ color: 'var(--primary)' }} />
            財政部電子發票大數據儀表板
          </h1>
          <p className="dashboard-subtitle">
            本地發票庫區間：{data?.summary?.minDate ? `${data.summary.minDate.replace(/-/g, '/')} ~ ${data.summary.maxDate.replace(/-/g, '/')}` : '無資料'}
            {data?.summary && (filterStartDate !== data.summary.minDate || filterEndDate !== data.summary.maxDate) && (
              <span style={{ marginLeft: '0.5rem', color: 'var(--primary)', fontWeight: 'bold' }}>
                （已篩選分析區間：{filterStartDate.replace(/-/g, '/')} ~ {filterEndDate.replace(/-/g, '/')}）
              </span>
            )}
          </p>
          
          {/* 自訂 100% 點擊式時間區段篩選器 (置於左側，完美貼合副標題之下) */}
          <div style={{ marginTop: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>篩選分析區間：</span>
            
            <div className="custom-calendar-container" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', position: 'relative' }}>
              {/* 起日選取 */}
              <div style={{ position: 'relative' }}>
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowStartCalendar(!showStartCalendar);
                    setShowEndCalendar(false);
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '32px',
                    boxSizing: 'border-box',
                    gap: '0.4rem',
                    padding: '0 0.8rem',
                    borderRadius: '20px',
                    border: showStartCalendar ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                    background: showStartCalendar ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                    color: 'var(--text-primary)',
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    boxShadow: showStartCalendar ? '0 0 10px rgba(99, 102, 241, 0.2)' : 'none',
                    transition: 'all 0.2s ease',
                    outline: 'none'
                  }}
                  onMouseEnter={(e) => {
                    if (!showStartCalendar) {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                      e.currentTarget.style.border = '1px solid rgba(99, 102, 241, 0.4)';
                      e.currentTarget.style.boxShadow = '0 0 8px rgba(99, 102, 241, 0.15)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!showStartCalendar) {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                      e.currentTarget.style.border = '1px solid var(--border-color)';
                      e.currentTarget.style.boxShadow = 'none';
                    }
                  }}
                >
                  <CalendarRange size={13} style={{ color: 'var(--primary)' }} />
                  <span>{filterStartDate ? filterStartDate.replace(/-/g, '/') : '選擇起日'}</span>
                </button>
                {showStartCalendar && renderCustomCalendar('start')}
              </div>

              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>至</span>

              {/* 迄日選取 */}
              <div style={{ position: 'relative' }}>
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowEndCalendar(!showEndCalendar);
                    setShowStartCalendar(false);
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '32px',
                    boxSizing: 'border-box',
                    gap: '0.4rem',
                    padding: '0 0.8rem',
                    borderRadius: '20px',
                    border: showEndCalendar ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                    background: showEndCalendar ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                    color: 'var(--text-primary)',
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    boxShadow: showEndCalendar ? '0 0 10px rgba(99, 102, 241, 0.2)' : 'none',
                    transition: 'all 0.2s ease',
                    outline: 'none'
                  }}
                  onMouseEnter={(e) => {
                    if (!showEndCalendar) {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                      e.currentTarget.style.border = '1px solid rgba(99, 102, 241, 0.4)';
                      e.currentTarget.style.boxShadow = '0 0 8px rgba(99, 102, 241, 0.15)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!showEndCalendar) {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                      e.currentTarget.style.border = '1px solid var(--border-color)';
                      e.currentTarget.style.boxShadow = 'none';
                    }
                  }}
                >
                  <CalendarRange size={13} style={{ color: 'var(--primary)' }} />
                  <span>{filterEndDate ? filterEndDate.replace(/-/g, '/') : '選擇迄日'}</span>
                </button>
                {showEndCalendar && renderCustomCalendar('end')}
              </div>

              {/* 重置按鈕 */}
              <button 
                onClick={() => {
                  if (data?.summary) {
                    setFilterStartDate(data.summary.minDate || '');
                    setFilterEndDate(data.summary.maxDate || '');
                    if (data.summary.minDate) {
                      const [y, m] = data.summary.minDate.split('-').map(Number);
                      setStartCalView({ year: y, month: m - 1 });
                    }
                    if (data.summary.maxDate) {
                      const [y, m] = data.summary.maxDate.split('-').map(Number);
                      setEndCalView({ year: y, month: m - 1 });
                    }
                  }
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '32px',
                  boxSizing: 'border-box',
                  padding: '0 1rem',
                  borderRadius: '20px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  border: '1px solid var(--border-color)',
                  background: 'rgba(255, 255, 255, 0.02)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  outline: 'none'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.border = '1px solid var(--primary)';
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                  e.currentTarget.style.color = 'var(--primary)';
                  e.currentTarget.style.boxShadow = '0 0 10px rgba(99, 102, 241, 0.25)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.border = '1px solid var(--border-color)';
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                重置
              </button>
            </div>
          </div>
        </div>
        
        {/* 右側：風格切換與同步控制 (運用絕對定位將風格置於同步上方，並將同步卡片對齊標題頂部) */}
        <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', marginTop: '1.25rem' }}>
          
          {/* 風格切換器 (極簡版：置於同步控制上方) */}
          <div className="glass-card theme-panel" style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.6rem', 
            padding: '0.4rem 0.8rem', 
            borderRadius: '10px',
            border: '1px solid var(--border-color)',
            background: 'rgba(255,255,255,0.02)',
            position: 'absolute',
            bottom: '100%',
            right: 0,
            marginBottom: '0.6rem',
            whiteSpace: 'nowrap'
          }}>
            <Palette size={14} style={{ color: 'var(--primary)' }} />
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {themes.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTheme(t.id)}
                  title={t.name}
                  style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    background: t.color,
                    border: activeTheme === t.id ? '2px solid #fff' : '2px solid transparent',
                    boxShadow: activeTheme === t.id ? '0 0 6px var(--primary)' : 'none',
                    cursor: 'pointer',
                    transform: activeTheme === t.id ? 'scale(1.15)' : 'scale(1)',
                    transition: 'all 0.2s ease',
                    padding: 0
                  }}
                />
              ))}
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', marginLeft: '0.25rem' }}>
              {themes.find(t => t.id === activeTheme)?.name}
            </span>
          </div>

          {/* 發票同步爬蟲控制台 */}
          <div className="glass-card crawler-panel" style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '1.25rem', 
            padding: '0.6rem 1.2rem', 
            borderRadius: '12px',
            border: '1px solid var(--border-color)',
            background: 'rgba(255,255,255,0.02)',
            margin: 0
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>本地最近一筆日期</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Calendar size={14} style={{ color: 'var(--primary)' }} />
                <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Outfit, sans-serif' }}>
                  {data?.summary?.maxDate ? data.summary.maxDate.replace(/-/g, '/') : '無資料'}
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
                margin={{ top: 10, right: 10, left: 15, bottom: 0 }}
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
                  width={65}
                  tickFormatter={(val) => `NT$${val}`}
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right"
                  stroke="var(--text-muted)"
                  fontSize={11}
                  tickLine={false}
                  width={40}
                  tickFormatter={(val) => `${val}張`}
                />
                <ChartTooltip 
                  contentStyle={{ 
                    background: 'var(--bg-secondary)', 
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
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
                    onClick={(data) => {
                      if (data && data.category) {
                        handleCategoryClick(data.category);
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    {categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[entry.category] || CATEGORY_COLORS['其它']} />
                    ))}
                  </Pie>
                  <ChartTooltip 
                    contentStyle={{ 
                      background: 'var(--bg-secondary)', 
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
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
                <div 
                  key={idx} 
                  onClick={() => handleCategoryClick(item.category)}
                  style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.5rem', 
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '6px',
                    transition: 'all 0.2s',
                    background: 'rgba(255,255,255,0.01)'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                    e.currentTarget.style.transform = 'translateX(2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.01)';
                    e.currentTarget.style.transform = 'translateX(0)';
                  }}
                >
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', flex: 1, padding: '0.1rem 0' }}>
            {topSellers.map((seller, idx) => {
              const maxAmount = topSellers[0]?.amount || 1;
              const percentage = (seller.amount / maxAmount) * 100;
              return (
                <div 
                  key={idx} 
                  className="seller-rank-row"
                  onClick={() => handleSellerClick(seller.sellerName)}
                  style={{ 
                    cursor: 'pointer', 
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0.32rem 0.6rem',
                    background: 'rgba(255, 255, 255, 0.005)',
                    border: '1px solid rgba(255, 255, 255, 0.015)',
                    borderRadius: '8px',
                    marginBottom: '0.05rem',
                    position: 'relative',
                    overflow: 'hidden'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateX(4px)';
                    e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--primary) 35%, transparent)';
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.08)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateX(0)';
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.015)';
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.005)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  {/* 1. 名次與店家名稱區塊 (固定寬度 140px，超過 8 字自動換行) */}
                  <div style={{ display: 'flex', alignItems: 'center', width: '140px', flexShrink: 0, gap: '0.45rem', zIndex: 2 }}>
                    <div 
                      className={`seller-rank-badge rank-${idx + 1}`} 
                      style={{ 
                        width: '18px', 
                        height: '18px', 
                        borderRadius: '5px', 
                        fontSize: '0.65rem', 
                        fontWeight: 700, 
                        flexShrink: 0 
                      }}
                    >
                      {idx + 1}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span 
                        className="seller-rank-name" 
                        style={{ 
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                          whiteSpace: 'normal',
                          wordBreak: 'break-all',
                          lineHeight: 1.15,
                          fontWeight: 600,
                          fontSize: '0.78rem',
                          color: 'var(--text-primary)',
                          maxWidth: '110px'
                        }}
                        title={seller.sellerName}
                      >
                        {seller.sellerName}
                      </span>
                    </div>
                  </div>

                  {/* 2. 金額與交易次數區塊 (固定寬度 95px，置中緊接在後) */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '95px', flexShrink: 0, paddingLeft: '0.25rem', zIndex: 2 }}>
                    <span className="seller-rank-amount" style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', fontFamily: 'Outfit, sans-serif' }}>
                      {formatCurrency(seller.amount)}
                    </span>
                    <span className="seller-rank-count" style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: '0.02rem' }}>
                      {seller.count}次交易
                    </span>
                  </div>

                  {/* 3. 右側長條圖對比區塊 (Flex: 1，所有店家基準線完美對齊，精準展現差距比例) */}
                  <div style={{ flex: 1, display: 'flex', alignItems: 'center', paddingLeft: '0.75rem', zIndex: 2 }}>
                    <div style={{ 
                      width: '100%', 
                      height: '14px', 
                      backgroundColor: 'rgba(255, 255, 255, 0.02)', 
                      borderRadius: '4px',
                      overflow: 'hidden',
                      border: '1px solid rgba(255, 255, 255, 0.03)',
                      boxShadow: 'inset 0 1px 2px rgba(0, 0, 0, 0.2)'
                    }}>
                      <div style={{ 
                        width: `${percentage}%`, 
                        height: '100%', 
                        background: idx % 2 === 0 ? 'var(--gradient-main)' : 'linear-gradient(90deg, var(--secondary) 0%, var(--accent) 100%)', 
                        borderRadius: '3px',
                        boxShadow: '0 0 5px var(--primary-glow)',
                        transition: 'width 1s cubic-bezier(0.16, 1, 0.3, 1)'
                      }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 分類與星期 2D 熱力圖 */}
        <div className="glass-card">
          <div className="chart-header">
            <h3 className="chart-title">
              <Calendar size={18} />
              分類與星期消費熱力圖 (分類 vs 星期)
            </h3>
          </div>
          
          <div className="heatmap-container">
            <div className="heatmap-legend">
              <span>少交易</span>
              <div className="legend-bar"></div>
              <span>多交易</span>
            </div>
            
            <div className="heatmap-grid-scroll">
              <div className="heatmap-grid" style={{ gridTemplateRows: 'repeat(9, auto)' }}>
                {/* 頂部星期標頭 */}
                <div className="heatmap-header-cell" style={{ fontWeight: 700 }}>分類 \ 星期</div>
                <div className="heatmap-header-cell">週一</div>
                <div className="heatmap-header-cell">週二</div>
                <div className="heatmap-header-cell">週三</div>
                <div className="heatmap-header-cell">週四</div>
                <div className="heatmap-header-cell">週五</div>
                <div className="heatmap-header-cell">週六</div>
                <div className="heatmap-header-cell">週日</div>
                
                {/* 分類與合計列渲染 */}
                {heatmapCategories.map((cat, catIdx) => (
                  <React.Fragment key={catIdx}>
                    {/* 左側分類標籤 */}
                    <div 
                      className="heatmap-label-cell" 
                      style={{ 
                        fontWeight: cat === '合計' ? 700 : 500,
                        color: cat === '合計' ? 'var(--primary)' : 'var(--text-secondary)',
                        background: cat === '合計' ? 'color-mix(in srgb, var(--primary) 8%, transparent)' : 'transparent',
                        borderRadius: '4px',
                        padding: '0.25rem 0.5rem',
                        fontSize: '0.78rem'
                      }}
                    >
                      {cat}
                    </div>
                    
                    {/* 星期一至日各區塊 */}
                    {weekdays.map((w, wIdx) => {
                      const cell = weekdayCategoryCells.find(c => c.weekday === w && c.category === cat) || { count: 0, amount: 0 };
                      
                      // 決定最大值進行透明度換算 (合計行與一般分類行分開計算，避免合計行過大導致一般行全白)
                      const isTotal = cat === '合計';
                      const maxLimit = isTotal ? maxTotalCellCount : maxCategoryCellCount;
                      const opacity = maxLimit > 0 ? (cell.count / maxLimit) * 0.8 + 0.15 : 0.06;
                      const hasData = cell.count > 0;
                      
                      return (
                        <div 
                          key={wIdx} 
                          className="heatmap-block"
                          style={{
                            backgroundColor: hasData 
                              ? (isTotal 
                                  ? `color-mix(in srgb, var(--secondary) ${opacity * 100}%, transparent)` 
                                  : `color-mix(in srgb, var(--primary) ${opacity * 100}%, transparent)`) 
                              : 'color-mix(in srgb, var(--text-muted) 5%, transparent)',
                            color: hasData ? 'var(--text-primary)' : 'var(--text-muted)',
                            border: hasData 
                              ? (isTotal 
                                  ? '1px solid var(--secondary)' 
                                  : '1px solid var(--primary)') 
                              : '1px solid var(--border-color)',
                            fontWeight: isTotal ? 700 : 500
                          }}
                        >
                          {cell.count > 0 ? cell.count : ''}
                          
                          {/* 懸停工具提示 */}
                          <div className="heatmap-tooltip">
                            <div style={{ fontWeight: 700, marginBottom: '0.2rem' }}>{w} • {cat}</div>
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
            
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem', marginTop: '0.75rem' }}>
              <Info size={12} />
              <span>格內數字為該星期該類別累積發票張數，滑鼠移入各個格子可檢視該分類於該星期的累計消費總金額與張數。最後一行為「合計」列。</span>
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
                                    backgroundColor: `color-mix(in srgb, ${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']} 15%, transparent)`,
                                    color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它'],
                                    border: `1px solid color-mix(in srgb, ${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']} 25%, transparent)`
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
          background: 'rgba(0, 0, 0, 0.5)',
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
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            border: '1px solid var(--border-color)',
            background: 'var(--bg-card)',
            overflow: 'hidden'
          }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div className="kpi-icon-container crimson" style={{ width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '10px' }}>
                  <AlertTriangle size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>退貨明細清單</h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    本地發票庫累計退貨：{summary.totalRefundCount} 筆，金額：{formatCurrency(Math.abs(summary.totalRefundAmount))}
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setShowRefundModal(false)}
                style={{
                  background: 'var(--border-color)',
                  border: 'none',
                  color: 'var(--text-primary)',
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
                onMouseLeave={(e) => e.target.style.background = 'var(--border-color)'}
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
                          background: 'var(--bg-item)',
                          width: '100%',
                          display: 'flex',
                          justifyContent: 'space-between',
                          padding: '1rem',
                          borderRadius: '8px',
                          border: '1px solid var(--border-item)',
                          alignItems: 'center'
                        }}
                      >
                        <div className="invoice-left" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <div className="invoice-icon" style={{ color: 'var(--danger)' }}>
                            <Receipt size={18} />
                          </div>
                          <div className="invoice-main-info" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span className="invoice-seller" style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.9rem' }}>{inv.sellerName}</span>
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
                                <tr style={{ borderBottom: '1px solid var(--border-table-header)', color: 'var(--text-muted)' }}>
                                  <th style={{ padding: '0.5rem 0.5rem 0.5rem 0' }}>退貨品項</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'center' }}>數量</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>單價</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>退款金額</th>
                                  <th style={{ padding: '0.5rem 0 0.5rem 0.5rem', textAlign: 'center' }}>分類</th>
                                </tr>
                              </thead>
                              <tbody>
                                {inv.items.filter(item => item.amount < 0).map((item, itemIdx) => (
                                  <tr key={itemIdx} style={{ borderBottom: '1px solid var(--border-table)' }}>
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
                                        backgroundColor: `color-mix(in srgb, ${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']} 15%, transparent)`,
                                        color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它'],
                                        border: `1px solid color-mix(in srgb, ${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']} 25%, transparent)`
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
            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
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

      {/* 分類明細彈出視窗 (Category Details Modal) */}
      {showCategoryModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(12px)',
          zIndex: 99999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem',
          animation: 'fadeIn 0.25s ease'
        }} onClick={() => setShowCategoryModal(false)}>
          <div className="glass-card" style={{
            maxWidth: '850px',
            width: '100%',
            maxHeight: '85vh',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            border: '1px solid var(--border-color)',
            background: 'var(--bg-card)',
            overflow: 'hidden'
          }} onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div 
                  className="kpi-icon-container" 
                  style={{ 
                    width: '40px', 
                    height: '40px', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center', 
                    borderRadius: '10px',
                    backgroundColor: `color-mix(in srgb, ${CATEGORY_COLORS[selectedCategory] || CATEGORY_COLORS['其它']} 20%, transparent)`,
                    color: CATEGORY_COLORS[selectedCategory] || CATEGORY_COLORS['其它']
                  }}
                >
                  <Receipt size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    【{selectedCategory}】消費明細清單
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    本地發票庫累計消費：{formatCurrency(categories.find(c => c.category === selectedCategory)?.amount || 0)}，共 {invoices.filter(inv => inv.items.some(item => item.category === selectedCategory)).length} 筆發票
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setShowCategoryModal(false)}
                style={{
                  background: 'var(--border-color)',
                  border: 'none',
                  color: 'var(--text-primary)',
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
                onMouseEnter={(e) => e.target.style.background = 'color-mix(in srgb, var(--primary) 20%, transparent)'}
                onMouseLeave={(e) => e.target.style.background = 'var(--border-color)'}
              >
                ✕
              </button>
            </div>

            {/* Modal Content - Invoices Scroll Area */}
            <div style={{ overflowY: 'auto', flex: 1, paddingRight: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {invoices.filter(inv => inv.items.some(item => item.category === selectedCategory)).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  <HelpCircle size={48} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                  <p>目前此分類下查無消費記錄</p>
                </div>
              ) : (
                invoices.filter(inv => inv.items.some(item => item.category === selectedCategory)).map((inv) => {
                  const isExpanded = expandedCategoryInvoices[inv.invNum] || false;
                  
                  // 計算該發票中屬於 selectedCategory 的品項金額總和
                  const categorySum = inv.items
                    .filter(item => item.category === selectedCategory)
                    .reduce((sum, item) => sum + item.amount, 0);

                  return (
                    <div key={inv.invNum} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <div 
                        className="invoice-item-row"
                        onClick={() => setExpandedCategoryInvoices(prev => ({ ...prev, [inv.invNum]: !prev[inv.invNum] }))}
                        style={{ 
                          cursor: 'pointer',
                          borderLeft: `4px solid ${CATEGORY_COLORS[selectedCategory] || CATEGORY_COLORS['其它']}`,
                          background: 'var(--bg-item)',
                          width: '100%',
                          display: 'flex',
                          justifyContent: 'space-between',
                          padding: '1rem',
                          borderRadius: '8px',
                          border: '1px solid var(--border-item)',
                          alignItems: 'center'
                        }}
                      >
                        <div className="invoice-left" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <div className="invoice-icon" style={{ color: CATEGORY_COLORS[selectedCategory] || CATEGORY_COLORS['其它'] }}>
                            <Receipt size={18} />
                          </div>
                          <div className="invoice-main-info" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span className="invoice-seller" style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.9rem' }}>{inv.sellerName}</span>
                            <div className="invoice-meta" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{inv.invNum}</span>
                              <span>•</span>
                              <span>{inv.date} {inv.invTime} ({inv.weekday})</span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="invoice-right" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                          <span className="invoice-amount-display normal" style={{ color: 'var(--text-primary)', fontWeight: 700, fontSize: '1.1rem' }}>
                            {formatCurrency(categorySum)}
                          </span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            <span>此類別含 {inv.items.filter(item => item.category === selectedCategory).length} 項商品</span>
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </div>
                        </div>
                      </div>

                      {/* Expandable items table */}
                      {isExpanded && (
                        <div style={{ 
                          background: 'var(--bg-table)',
                          border: '1px solid var(--border-table)',
                          borderRadius: '12px',
                          padding: '1rem',
                          marginLeft: '0.25rem',
                          marginBottom: '0.5rem',
                          animation: 'fadeIn 0.2s ease'
                        }}>
                          <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                              <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-table-header)', color: 'var(--text-muted)' }}>
                                  <th style={{ padding: '0.5rem 0.5rem 0.5rem 0' }}>商品品項</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'center' }}>數量</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>單價</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>金額</th>
                                </tr>
                              </thead>
                              <tbody>
                                {inv.items.filter(item => item.category === selectedCategory).map((item, itemIdx) => (
                                  <tr key={itemIdx} style={{ borderBottom: '1px solid var(--border-table)' }}>
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
            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
              <button 
                onClick={() => setShowCategoryModal(false)}
                className="chart-btn active"
                style={{ padding: '0.5rem 1.5rem', borderRadius: '8px' }}
              >
                關閉視窗
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 店家消費明細彈出視窗 (Seller Details Modal) */}
      {showSellerModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(12px)',
          zIndex: 99999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem',
          animation: 'fadeIn 0.25s ease'
        }} onClick={() => setShowSellerModal(false)}>
          <div className="glass-card" style={{
            maxWidth: '850px',
            width: '100%',
            maxHeight: '85vh',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            border: '1px solid var(--border-color)',
            background: 'var(--bg-card)',
            overflow: 'hidden'
          }} onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div 
                  className="kpi-icon-container" 
                  style={{ 
                    width: '40px', 
                    height: '40px', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center', 
                    borderRadius: '10px',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    color: 'var(--primary)'
                  }}
                >
                  <Building size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    【{selectedSeller}】店內消費品項明細
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    本地發票庫累計消費：{formatCurrency(topSellers.find(s => s.sellerName === selectedSeller)?.amount || 0)}，共 {invoices.filter(inv => inv.sellerName === selectedSeller).length} 筆交易
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setShowSellerModal(false)}
                style={{
                  background: 'var(--border-color)',
                  border: 'none',
                  color: 'var(--text-primary)',
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
                onMouseEnter={(e) => e.target.style.background = 'color-mix(in srgb, var(--primary) 20%, transparent)'}
                onMouseLeave={(e) => e.target.style.background = 'var(--border-color)'}
              >
                ✕
              </button>
            </div>

            {/* Modal Content - Invoices Scroll Area */}
            <div style={{ overflowY: 'auto', flex: 1, paddingRight: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {invoices.filter(inv => inv.sellerName === selectedSeller).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  <HelpCircle size={48} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                  <p>目前此店家下查無消費記錄</p>
                </div>
              ) : (
                invoices.filter(inv => inv.sellerName === selectedSeller).map((inv) => {
                  const isExpanded = expandedSellerInvoices[inv.invNum] || false;
                  
                  return (
                    <div key={inv.invNum} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <div 
                        className="invoice-item-row"
                        onClick={() => setExpandedSellerInvoices(prev => ({ ...prev, [inv.invNum]: !prev[inv.invNum] }))}
                        style={{ 
                          cursor: 'pointer',
                          borderLeft: '4px solid var(--primary)',
                          background: 'var(--bg-item)',
                          width: '100%',
                          display: 'flex',
                          justifyContent: 'space-between',
                          padding: '1rem',
                          borderRadius: '8px',
                          border: '1px solid var(--border-item)',
                          alignItems: 'center'
                        }}
                      >
                        <div className="invoice-left" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <div className="invoice-icon" style={{ color: 'var(--primary)' }}>
                            <Receipt size={18} />
                          </div>
                          <div className="invoice-main-info" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span className="invoice-seller" style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.9rem' }}>{inv.sellerName}</span>
                            <div className="invoice-meta" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{inv.invNum}</span>
                              <span>•</span>
                              <span>{inv.date} {inv.invTime} ({inv.weekday})</span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="invoice-right" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                          <span className="invoice-amount-display normal" style={{ color: 'var(--text-primary)', fontWeight: 700, fontSize: '1.1rem' }}>
                            {formatCurrency(inv.amount)}
                          </span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            <span>共 {inv.items.length} 項商品</span>
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </div>
                        </div>
                      </div>

                      {/* Expandable items table */}
                      {isExpanded && (
                        <div style={{ 
                          background: 'var(--bg-table)',
                          border: '1px solid var(--border-table)',
                          borderRadius: '12px',
                          padding: '1rem',
                          marginLeft: '0.25rem',
                          marginBottom: '0.5rem',
                          animation: 'fadeIn 0.2s ease'
                        }}>
                          <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                              <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-table-header)', color: 'var(--text-muted)' }}>
                                  <th style={{ padding: '0.5rem 0.5rem 0.5rem 0' }}>商品品項</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'center' }}>數量</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>單價</th>
                                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>金額</th>
                                </tr>
                              </thead>
                              <tbody>
                                {inv.items.map((item, itemIdx) => (
                                  <tr key={itemIdx} style={{ borderBottom: '1px solid var(--border-table)' }}>
                                    <td style={{ padding: '0.65rem 0.5rem 0.65rem 0', fontWeight: 500, color: 'var(--text-primary)' }}>
                                      {item.itemName}
                                      <span 
                                        style={{ 
                                          marginLeft: '0.5rem', 
                                          padding: '0.1rem 0.35rem', 
                                          borderRadius: '4px', 
                                          fontSize: '0.62rem', 
                                          fontWeight: 600,
                                          background: `color-mix(in srgb, ${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']} 15%, transparent)`,
                                          color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它'],
                                          border: `1px solid color-mix(in srgb, ${CATEGORY_COLORS[item.category] || CATEGORY_COLORS['其它']} 25%, transparent)`
                                        }}
                                      >
                                        {item.category}
                                      </span>
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
            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
              <button 
                onClick={() => setShowSellerModal(false)}
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
