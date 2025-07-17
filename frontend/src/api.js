import axios from 'axios';

// Create axios instance
const api = axios.create({
    baseURL: process.env.NODE_ENV === 'development' 
        ? 'http://localhost:5000'  // Flask port
        : ''  // Production path (relative)
});

// Validation API
export const validateFile = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await api.post('/validate', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        return response.data;
    } catch (error) {
        throw error.response?.data || error.message;
    }
};

// Export API
export const exportResults = async (results) => {
    try {
        const response = await api.post('/export', results, {
            responseType: 'blob'  // Important for file download
        });
        return response;
    } catch (error) {
        throw error.response?.data || error.message;
    }
};