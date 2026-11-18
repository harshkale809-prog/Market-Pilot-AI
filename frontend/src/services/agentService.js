import api from './api';

export const generateMarketingPlan = async (payload) => {
    // Accepts either string (simple goal) or structured object (goal, timeline, budget, re-plan params)
    const requestBody = typeof payload === 'string' ? { goal: payload } : payload;
    const response = await api.post('/agent/plan', requestBody);
    return response.data;
};
