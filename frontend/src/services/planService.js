import api from './api';

export const getPlans = async () => {
    const response = await api.get('/plans');
    return response.data;
};

export const renamePlan = async (planId, newTitle) => {
    const response = await api.put(`/plans/${planId}`, { title: newTitle });
    return response.data;
};

export const deletePlan = async (planId) => {
    await api.delete(`/plans/${planId}`);
};