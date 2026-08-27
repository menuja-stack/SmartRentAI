import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../api/axios';

export const loginUser = createAsyncThunk('auth/login', async (creds, { rejectWithValue }) => {
  try {
    const { data } = await api.post('/auth/login', creds);
    localStorage.setItem('token', data.token);
    return data;
  } catch (err) {
    return rejectWithValue(err.response?.data?.error || 'Login failed');
  }
});

export const registerUser = createAsyncThunk('auth/register', async (payload, { rejectWithValue }) => {
  try {
    const { data } = await api.post('/auth/register', payload);
    localStorage.setItem('token', data.token);
    return data;
  } catch (err) {
    return rejectWithValue(err.response?.data?.error || 'Registration failed');
  }
});

export const fetchMe = createAsyncThunk('auth/me', async (_, { rejectWithValue }) => {
  try {
    const { data } = await api.get('/auth/me');
    return data;
  } catch (err) {
    return rejectWithValue(err.response?.data?.error);
  }
});

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user:    null,
    token:   localStorage.getItem('token'),
    loading: false,
    error:   null,
  },
  reducers: {
    logout(state) {
      state.user  = null;
      state.token = null;
      localStorage.removeItem('token');
    },
    clearError(state) { state.error = null; },
  },
  extraReducers(builder) {
    const pending  = (s) => { s.loading = true;  s.error = null; };
    const rejected = (s, a) => { s.loading = false; s.error = a.payload; };

    builder
      .addCase(loginUser.pending,    pending)
      .addCase(loginUser.rejected,   rejected)
      .addCase(loginUser.fulfilled,  (s, a) => { s.loading = false; s.user = a.payload.user; s.token = a.payload.token; })
      .addCase(registerUser.pending,   pending)
      .addCase(registerUser.rejected,  rejected)
      .addCase(registerUser.fulfilled, (s, a) => { s.loading = false; s.user = a.payload.user; s.token = a.payload.token; })
      .addCase(fetchMe.fulfilled, (s, a) => { s.user = a.payload; });
  },
});

export const { logout, clearError } = authSlice.actions;
export default authSlice.reducer;
