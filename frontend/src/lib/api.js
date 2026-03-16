import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 10000,
});

export const getErrorMessage = (error, fallback = "Request failed") => {
  return error?.response?.data?.detail || error?.message || fallback;
};
