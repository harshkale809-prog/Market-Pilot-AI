import React, { useState, useEffect } from 'react';
import { uploadKnowledgePdf, uploadKnowledgeUrl } from '../services/documentService';
import { generateMarketingPlan } from '../services/agentService';
import { getPlans, renamePlan, deletePlan } from '../services/planService';
import { removeToken } from '../utils/auth';
import { useNavigate } from 'react-router-dom';
import { 
    UploadCloud, Play, LogOut, FileText, CheckCircle, AlertCircle, 
    Loader2, Moon, Sun, Edit2, Trash2, X, Sparkles, Globe, Bot,
    RotateCcw, Calendar, Sliders, AlertTriangle, ArrowRight, CheckSquare
} from 'lucide-react';

const Dashboard = () => {
    const navigate = useNavigate();
    
    // State
    const [file, setFile] = useState(null);
    const [urlInput, setUrlInput] = useState('');
    const [goal, setGoal] = useState('');
    const [plans, setPlans] = useState([]);
    const [selectedPlan, setSelectedPlan] = useState(null);
    const [isDarkMode, setIsDarkMode] = useState(false);

    // Advanced Discovery Questions State (Before Generation)
    const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
    const [timeline, setTimeline] = useState('4 Weeks');
    const [budget, setBudget] = useState('Medium ($1k - $5k)');
    const [targetAudience, setTargetAudience] = useState('');
    const [primaryChannels, setPrimaryChannels] = useState('Social Media, Email');

    // Adaptive Re-Planning Modal State (When Deadlines are Missed)
    const [showReplanModal, setShowReplanModal] = useState(false);
    const [missedTasks, setMissedTasks] = useState('');
    const [daysDelayed, setDaysDelayed] = useState(5);
    const [adjustmentStrategy, setAdjustmentStrategy] = useState('extend');
    
    // Loading & Status States
    const [isUploading, setIsUploading] = useState(false);
    const [isScraping, setIsScraping] = useState(false);
    const [isPlanning, setIsPlanning] = useState(false);
    const [statusMsg, setStatusMsg] = useState({ type: '', text: '' });
    const [editingPlanId, setEditingPlanId] = useState(null);
    const [newTitle, setNewTitle] = useState('');

    const fetchPlans = async () => {
        try {
            const data = await getPlans();
            setPlans(data);
        } catch (error) {
            setStatusMsg({ type: 'error', text: error.response?.data?.detail || error.message || 'Failed to load history.' });
        }
    };

    useEffect(() => {
        fetchPlans();
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
            setIsDarkMode(true);
        } else {
            document.documentElement.classList.remove('dark');
            setIsDarkMode(false);
        }
    }, []);

    const toggleDarkMode = () => {
        const root = document.documentElement;
        if (root.classList.contains('dark')) {
            root.classList.remove('dark');
            localStorage.setItem('theme', 'light');
            setIsDarkMode(false);
        } else {
            root.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            setIsDarkMode(true);
        }
    };

    const handleGeneratePlan = async (e) => {
        e.preventDefault();
        if (!goal.trim()) return;
        setIsPlanning(true);
        setStatusMsg({ type: '', text: '' });
        
        try {
            const payload = {
                goal: goal.trim(),
                timeline: showAdvancedOptions ? timeline : undefined,
                budget: showAdvancedOptions ? budget : undefined,
                target_audience: showAdvancedOptions && targetAudience.trim() ? targetAudience.trim() : undefined,
                primary_channels: showAdvancedOptions ? primaryChannels : undefined
            };

            const result = await generateMarketingPlan(payload);
            setStatusMsg({ type: 'success', text: 'MarketPilot AI plan generated successfully!' });
            await fetchPlans();
            setSelectedPlan({ title: goal, content: result.plan, id: result.plan_id });
            setGoal('');
        } catch (error) {
            const errorDetail = error.response?.data?.detail || error.message || 'Failed to generate plan.';
            setStatusMsg({ type: 'error', text: errorDetail });
        } finally {
            setIsPlanning(false);
        }
    };

    // Handler to execute adaptive re-planning when deadlines are missed
    const handleReplanSubmit = async (e) => {
        e.preventDefault();
        if (!selectedPlan) return;
        setIsPlanning(true);
        setStatusMsg({ type: '', text: '' });
        setShowReplanModal(false);

        try {
            const payload = {
                goal: selectedPlan.title.replace(/^Strategy: |^Recovery Plan: /i, ''),
                is_replanned: true,
                missed_tasks: missedTasks.trim() || 'General milestone delays',
                days_delayed: parseInt(daysDelayed) || 5,
                adjustment_strategy: adjustmentStrategy,
                original_plan_summary: selectedPlan.content.replace(/<[^>]*>?/gm, '').slice(0, 1000)
            };

            const result = await generateMarketingPlan(payload);
            setStatusMsg({ type: 'success', text: 'Adaptive Recovery Plan generated successfully with adjusted deadlines!' });
            await fetchPlans();
            setSelectedPlan({ title: `Recovery Plan: ${selectedPlan.title}`, content: result.plan, id: result.plan_id });
            setMissedTasks('');
        } catch (error) {
            const errorDetail = error.response?.data?.detail || error.message || 'Failed to generate recovery plan.';
            setStatusMsg({ type: 'error', text: errorDetail });
        } finally {
            setIsPlanning(false);
        }
    };

    const handleDelete = async (id, e) => {
        e.stopPropagation();
        if (!window.confirm('Are you sure you want to delete this marketing plan?')) return;
        try {
            await deletePlan(id);
            if (selectedPlan?.id === id) setSelectedPlan(null);
            fetchPlans();
            setStatusMsg({ type: 'success', text: 'Plan deleted successfully.' });
        } catch (error) {
            setStatusMsg({ type: 'error', text: 'Failed to delete plan.' });
        }
    };

    const handleRename = async (id, e) => {
        e.stopPropagation();
        if (!newTitle.trim()) return;
        try {
            await renamePlan(id, newTitle.trim());
            setEditingPlanId(null);
            if (selectedPlan?.id === id) {
                setSelectedPlan({ ...selectedPlan, title: newTitle.trim() });
            }
            fetchPlans();
            setStatusMsg({ type: 'success', text: 'Plan title updated.' });
        } catch (error) {
            setStatusMsg({ type: 'error', text: 'Failed to rename plan.' });
        }
    };

    const handleFileUpload = async (e) => {
        e.preventDefault();
        if (!file) return;

        setIsUploading(true);
        setStatusMsg({ type: '', text: '' });
        try {
            const result = await uploadKnowledgePdf(file); 
            setStatusMsg({ type: 'success', text: result.message || 'PDF uploaded and vectorized successfully!' });
            setFile(null);
            e.target.reset();
        } catch (error) {
            const errorDetail = error.response?.data?.detail || 'Failed to upload document. Please check the file.';
            setStatusMsg({ type: 'error', text: errorDetail });
        } finally {
            setIsUploading(false);
        }
    };

    const handleUrlUpload = async (e) => {
        e.preventDefault();
        if (!urlInput.trim()) return;

        setIsScraping(true);
        setStatusMsg({ type: '', text: '' });
        try {
            const result = await uploadKnowledgeUrl(urlInput.trim());
            setStatusMsg({ type: 'success', text: result.message || 'URL content scraped and vectorized successfully!' });
            setUrlInput('');
        } catch (error) {
            const errorDetail = error.response?.data?.detail || 'Failed to scrape URL. Please check the web address.';
            setStatusMsg({ type: 'error', text: errorDetail });
        } finally {
            setIsScraping(false);
        }
    };

    return (
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
            
            {/* LEFT SIDEBAR: History & Branding */}
            <div className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full shadow-sm">
                
                {/* Brand Header */}
                <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-blue-600/5 dark:bg-blue-900/10">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-sm">
                            <Bot className="w-5 h-5" />
                        </div>
                        <div>
                            <h1 className="font-bold text-gray-900 dark:text-white text-base leading-tight">MARKET PILOT AI</h1>
                            <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">Adaptive Multi-Agent SaaS</p>
                        </div>
                    </div>
                    <button 
                        onClick={toggleDarkMode} 
                        title="Toggle dark/light mode"
                        className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 transition-colors"
                    >
                        {isDarkMode ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5" />}
                    </button>
                </div>

                {/* Plan History Header */}
                <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700/50 flex items-center justify-between">
                    <h2 className="font-semibold text-gray-700 dark:text-gray-200 text-sm flex items-center gap-2">
                        <FileText className="w-4 h-4 text-blue-500" /> Plan History
                    </h2>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                        {plans.length}
                    </span>
                </div>
                
                {/* Plan List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {plans.map((plan) => {
                        const isRecovery = plan.title.toLowerCase().includes('recovery plan');
                        return (
                            <div 
                                key={plan.id} 
                                onClick={() => setSelectedPlan(plan)}
                                className={`p-3 rounded-xl border cursor-pointer transition-all group ${
                                    selectedPlan?.id === plan.id 
                                        ? 'bg-blue-50 border-blue-300 dark:bg-blue-950/40 dark:border-blue-700 shadow-xs' 
                                        : 'bg-white border-gray-100 hover:border-blue-200 dark:bg-gray-800 dark:border-gray-700 dark:hover:border-gray-600'
                                }`}
                            >
                                {editingPlanId === plan.id ? (
                                    <div className="flex items-center gap-2">
                                        <input 
                                            type="text" 
                                            autoFocus
                                            className="flex-1 px-2 py-1 text-sm border border-blue-400 rounded bg-white dark:bg-gray-700 dark:text-white outline-none"
                                            value={newTitle} 
                                            onChange={(e) => setNewTitle(e.target.value)}
                                            onClick={(e) => e.stopPropagation()}
                                            onKeyDown={(e) => e.key === 'Enter' && handleRename(plan.id, e)}
                                        />
                                        <button 
                                            onClick={(e) => handleRename(plan.id, e)}
                                            title="Save title"
                                            className="p-1 hover:bg-green-50 dark:hover:bg-green-900/30 rounded"
                                        >
                                            <CheckCircle className="w-4 h-4 text-green-500"/>
                                        </button>
                                        <button 
                                            onClick={(e) => { e.stopPropagation(); setEditingPlanId(null); }}
                                            title="Cancel"
                                            className="p-1 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
                                        >
                                            <X className="w-4 h-4 text-red-500"/>
                                        </button>
                                    </div>
                                ) : (
                                    <div className="flex justify-between items-start">
                                        <div className="pr-2 flex-1 min-w-0">
                                            {isRecovery && (
                                                <span className="inline-block text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 mb-1">
                                                    Adaptive Re-Plan
                                                </span>
                                            )}
                                            <h4 className="font-semibold text-gray-800 dark:text-gray-200 text-sm truncate">{plan.title}</h4>
                                            <p className="text-xs text-gray-400 mt-1">{new Date(plan.created_at).toLocaleString()}</p>
                                        </div>
                                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); setEditingPlanId(plan.id); setNewTitle(plan.title); }} 
                                                title="Rename plan"
                                                className="p-1 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 rounded"
                                            >
                                                <Edit2 className="w-3.5 h-3.5"/>
                                            </button>
                                            <button 
                                                onClick={(e) => handleDelete(plan.id, e)} 
                                                title="Delete plan"
                                                className="p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 rounded"
                                            >
                                                <Trash2 className="w-3.5 h-3.5"/>
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                    {plans.length === 0 && (
                        <div className="text-center py-10 px-4">
                            <FileText className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                            <p className="text-sm text-gray-400">No marketing plans saved yet.</p>
                            <p className="text-xs text-gray-400 mt-1">Generate your first plan below.</p>
                        </div>
                    )}
                </div>
                
                {/* Logout Footer */}
                <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
                    <button 
                        onClick={() => { removeToken(); navigate('/login'); }} 
                        className="flex items-center gap-2 w-full px-4 py-2.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors font-medium text-sm"
                    >
                        <LogOut className="w-4 h-4" /> Sign Out
                    </button>
                </div>
            </div>

            {/* MAIN CONTENT AREA */}
            <div className="flex-1 flex flex-col h-full overflow-y-auto">
                <div className="p-8 max-w-5xl mx-auto w-full">
                    
                    {/* Status Alerts */}
                    {statusMsg.text && (
                        <div className={`mb-6 p-4 rounded-xl flex items-center justify-between gap-3 font-medium text-sm shadow-xs ${
                            statusMsg.type === 'error' 
                                ? 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800' 
                                : 'bg-green-50 text-green-700 border border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800'
                        }`}>
                            <div className="flex items-center gap-3">
                                {statusMsg.type === 'error' ? <AlertCircle className="w-5 h-5 shrink-0" /> : <CheckCircle className="w-5 h-5 shrink-0" />}
                                <span>{statusMsg.text}</span>
                            </div>
                            <button onClick={() => setStatusMsg({ type: '', text: '' })} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    )}

                    {/* Knowledge Base Context Engine */}
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 mb-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                                <UploadCloud className="w-5 h-5 text-blue-600" /> Knowledge Base Context (RAG)
                            </h3>
                            <span className="text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2.5 py-1 rounded-full font-medium">
                                Multi-Tenant Isolated
                            </span>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* PDF Upload */}
                            <form onSubmit={handleFileUpload} className="border border-gray-200 dark:border-gray-600 rounded-xl p-4 flex flex-col gap-3 bg-gray-50/50 dark:bg-gray-700/30">
                                <label className="text-xs font-semibold text-gray-600 dark:text-gray-300 flex items-center gap-1.5">
                                    <FileText className="w-3.5 h-3.5 text-blue-500" /> Upload PDF Document
                                </label>
                                <div className="flex items-center gap-2">
                                    <input 
                                        type="file" 
                                        accept="application/pdf" 
                                        onChange={(e) => setFile(e.target.files[0])} 
                                        className="flex-1 text-xs text-gray-600 dark:text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-900/40 dark:file:text-blue-300"
                                    />
                                    <button 
                                        type="submit" 
                                        disabled={!file || isUploading}
                                        className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg disabled:opacity-50 transition-colors shrink-0 flex items-center gap-1.5"
                                    >
                                        {isUploading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                        {isUploading ? 'Ingesting...' : 'Ingest PDF'}
                                    </button>
                                </div>
                            </form>

                            {/* URL Scraper */}
                            <form onSubmit={handleUrlUpload} className="border border-gray-200 dark:border-gray-600 rounded-xl p-4 flex flex-col gap-3 bg-gray-50/50 dark:bg-gray-700/30">
                                <label className="text-xs font-semibold text-gray-600 dark:text-gray-300 flex items-center gap-1.5">
                                    <Globe className="w-3.5 h-3.5 text-blue-500" /> Scrape Web Resource
                                </label>
                                <div className="flex items-center gap-2">
                                    <input 
                                        type="url" 
                                        placeholder="https://example.com/marketing-report"
                                        value={urlInput}
                                        onChange={(e) => setUrlInput(e.target.value)}
                                        className="flex-1 px-3 py-1.5 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                                    />
                                    <button 
                                        type="submit" 
                                        disabled={!urlInput.trim() || isScraping}
                                        className="px-3.5 py-1.5 bg-gray-900 hover:bg-black dark:bg-gray-600 dark:hover:bg-gray-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50 transition-colors shrink-0 flex items-center gap-1.5"
                                    >
                                        {isScraping && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                        {isScraping ? 'Scraping...' : 'Add Web URL'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>

                    {/* Generator Controls with Guided Questionnaire */}
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 mb-8">
                        <div className="flex items-center justify-between mb-2">
                            <label className="text-sm font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                                <Sparkles className="w-4 h-4 text-blue-600" /> Generate New Marketing Campaign Plan
                            </label>
                            <button
                                type="button"
                                onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                                className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 font-semibold"
                            >
                                <Sliders className="w-3.5 h-3.5" />
                                {showAdvancedOptions ? 'Hide Planning Questions' : 'Customize Strategy Questions (Timeline, Budget, Audience)'}
                            </button>
                        </div>

                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                            Describe your marketing objective. The multi-agent crew (Strategist, Execution Planner, Publisher) will formulate a structured campaign.
                        </p>

                        {/* Interactive Guided Questions */}
                        {showAdvancedOptions && (
                            <div className="p-4 mb-4 rounded-xl bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/30 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                                <div>
                                    <label className="font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                                        Target Timeline
                                    </label>
                                    <select 
                                        value={timeline} 
                                        onChange={(e) => setTimeline(e.target.value)}
                                        className="w-full p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white"
                                    >
                                        <option value="2 Weeks (Sprint Launch)">2 Weeks (Sprint Launch)</option>
                                        <option value="4 Weeks (Standard Campaign)">4 Weeks (Standard Campaign)</option>
                                        <option value="8 Weeks (Full Market Entry)">8 Weeks (Full Market Entry)</option>
                                        <option value="Quarterly (3 Months Enterprise)">Quarterly (3 Months Enterprise)</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                                        Budget Level
                                    </label>
                                    <select 
                                        value={budget} 
                                        onChange={(e) => setBudget(e.target.value)}
                                        className="w-full p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white"
                                    >
                                        <option value="Bootstrap / Zero-Budget Organic">Bootstrap / Zero-Budget Organic</option>
                                        <option value="Low ($500 - $2,000)">Low ($500 - $2,000)</option>
                                        <option value="Medium ($2,000 - $10,000)">Medium ($2,000 - $10,000)</option>
                                        <option value="High ($10,000+ Scaled Ads & PR)">High ($10,000+ Scaled Ads & PR)</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                                        Target Audience
                                    </label>
                                    <input 
                                        type="text"
                                        placeholder="e.g., College students, B2B CTOs, Gen-Z consumers"
                                        value={targetAudience}
                                        onChange={(e) => setTargetAudience(e.target.value)}
                                        className="w-full p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white"
                                    />
                                </div>

                                <div>
                                    <label className="font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                                        Primary Marketing Channels
                                    </label>
                                    <input 
                                        type="text"
                                        placeholder="e.g., Instagram, LinkedIn, Influencer Outreach, SEO"
                                        value={primaryChannels}
                                        onChange={(e) => setPrimaryChannels(e.target.value)}
                                        className="w-full p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white"
                                    />
                                </div>
                            </div>
                        )}

                        <div className="flex gap-3 items-center">
                            <input 
                                type="text" 
                                className="flex-1 p-3.5 border border-gray-200 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none bg-gray-50 dark:bg-gray-700 dark:text-white text-sm"
                                placeholder="e.g. Launch campaign for a new electric scooter targeting young professionals..."
                                value={goal}
                                onChange={(e) => setGoal(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && !isPlanning && handleGeneratePlan(e)}
                                disabled={isPlanning}
                            />
                            <button 
                                onClick={handleGeneratePlan}
                                disabled={!goal.trim() || isPlanning}
                                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 text-white font-semibold py-3.5 px-6 rounded-xl transition-all text-sm shrink-0 shadow-sm"
                            >
                                {isPlanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                                {isPlanning ? 'Orchestrating Agents...' : 'Generate Plan'}
                            </button>
                        </div>
                    </div>

                    {/* HTML Document Viewer with Adaptive Re-Planning Toolbar */}
                    {selectedPlan ? (
                        <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                            
                            {/* Document Header & Re-Plan Action Banner */}
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-4 border-b border-gray-100 dark:border-gray-700">
                                <div>
                                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                                        {selectedPlan.title}
                                    </h2>
                                    {selectedPlan.created_at && (
                                        <p className="text-xs text-gray-400 mt-1">Generated: {new Date(selectedPlan.created_at).toLocaleString()}</p>
                                    )}
                                </div>

                                <div className="flex items-center gap-3">
                                    {/* Teacher-requested Feature: Missed Deadline Re-Plan Button */}
                                    <button
                                        onClick={() => setShowReplanModal(true)}
                                        disabled={isPlanning}
                                        title="Missed a deadline or fallen behind? Re-calculate the plan!"
                                        className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl text-xs shadow-sm transition-all hover:shadow"
                                    >
                                        <RotateCcw className="w-3.5 h-3.5" />
                                        Missed Deadlines? Re-Plan Here
                                    </button>

                                    <span className="text-xs px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-semibold">
                                        Active Plan
                                    </span>
                                </div>
                            </div>
                            
                            {/* Formatted Semantic HTML Content */}
                            <div 
                                className="prose prose-blue dark:prose-invert max-w-none prose-headings:font-bold prose-a:text-blue-600"
                                dangerouslySetInnerHTML={{ __html: selectedPlan.content }}
                            />
                        </div>
                    ) : (
                        <div className="bg-white dark:bg-gray-800/50 border border-dashed border-gray-200 dark:border-gray-700 rounded-2xl text-center py-20 px-4">
                            <div className="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center mx-auto mb-4">
                                <FileText className="w-8 h-8 opacity-75" />
                            </div>
                            <h3 className="text-lg font-bold text-gray-700 dark:text-gray-200">No Plan Selected</h3>
                            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1 max-w-md mx-auto">
                                Select a previously saved plan from the sidebar history or generate a brand new campaign plan using the generator above.
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* ADAPTIVE RE-PLANNING MODAL (Triggered when deadlines are missed) */}
            {showReplanModal && (
                <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-lg w-full border border-gray-200 dark:border-gray-700 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
                        
                        <div className="p-5 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between bg-amber-500/10">
                            <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-bold text-base">
                                <AlertTriangle className="w-5 h-5" />
                                <h3>Adaptive Re-Planning (Missed Deadlines)</h3>
                            </div>
                            <button 
                                onClick={() => setShowReplanModal(false)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleReplanSubmit} className="p-6 space-y-4">
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                Tell MarketPilot AI what changed or what deadlines slipped. The agents will re-evaluate your critical path and produce a modified catch-up plan.
                            </p>

                            {/* Missed Tasks Question */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                                    1. Which tasks, phases, or deliverables were missed?
                                </label>
                                <textarea 
                                    rows="2"
                                    required
                                    placeholder="e.g., Week 1 influencer outreach not started, social media graphics delayed by 4 days"
                                    value={missedTasks}
                                    onChange={(e) => setMissedTasks(e.target.value)}
                                    className="w-full p-2.5 text-xs rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-white outline-none focus:ring-2 focus:ring-amber-500"
                                />
                            </div>

                            {/* Days Delayed Question */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                                    2. Approximately how many days behind schedule are you?
                                </label>
                                <div className="flex items-center gap-3">
                                    <input 
                                        type="number"
                                        min="1"
                                        max="90"
                                        value={daysDelayed}
                                        onChange={(e) => setDaysDelayed(e.target.value)}
                                        className="w-24 p-2 text-xs rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-white outline-none focus:ring-2 focus:ring-amber-500"
                                    />
                                    <span className="text-xs text-gray-500 dark:text-gray-400">days delayed</span>
                                </div>
                            </div>

                            {/* Adjustment Strategy Question */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                                    3. What recovery strategy would you like the agents to use?
                                </label>
                                <div className="space-y-2">
                                    <label className="flex items-start gap-2 p-2.5 rounded-xl border border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                        <input 
                                            type="radio" 
                                            name="strategy" 
                                            value="extend" 
                                            checked={adjustmentStrategy === 'extend'} 
                                            onChange={(e) => setAdjustmentStrategy(e.target.value)}
                                            className="mt-0.5" 
                                        />
                                        <div className="text-xs">
                                            <span className="font-semibold text-gray-800 dark:text-gray-200 block">Shift & Extend Timeline</span>
                                            <span className="text-gray-500 dark:text-gray-400">Keep all tasks intact but push future dates back accordingly.</span>
                                        </div>
                                    </label>

                                    <label className="flex items-start gap-2 p-2.5 rounded-xl border border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                        <input 
                                            type="radio" 
                                            name="strategy" 
                                            value="compress" 
                                            checked={adjustmentStrategy === 'compress'} 
                                            onChange={(e) => setAdjustmentStrategy(e.target.value)}
                                            className="mt-0.5" 
                                        />
                                        <div className="text-xs">
                                            <span className="font-semibold text-gray-800 dark:text-gray-200 block">Compress & Fast-Track (Keep Hard Deadline)</span>
                                            <span className="text-gray-500 dark:text-gray-400">Double up tasks and optimize sprints to hit the original end date.</span>
                                        </div>
                                    </label>

                                    <label className="flex items-start gap-2 p-2.5 rounded-xl border border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                        <input 
                                            type="radio" 
                                            name="strategy" 
                                            value="re-prioritize" 
                                            checked={adjustmentStrategy === 're-prioritize'} 
                                            onChange={(e) => setAdjustmentStrategy(e.target.value)}
                                            className="mt-0.5" 
                                        />
                                        <div className="text-xs">
                                            <span className="font-semibold text-gray-800 dark:text-gray-200 block">Drop Non-Critical Tasks (Agile Recovery)</span>
                                            <span className="text-gray-500 dark:text-gray-400">Focus solely on high-impact MVP tasks; discard low-ROI activities.</span>
                                        </div>
                                    </label>
                                </div>
                            </div>

                            <div className="pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowReplanModal(false)}
                                    className="px-4 py-2 text-xs font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-5 py-2 text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-white rounded-xl shadow-sm transition-all flex items-center gap-1.5"
                                >
                                    <RotateCcw className="w-3.5 h-3.5" />
                                    Generate Recovery Plan
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
