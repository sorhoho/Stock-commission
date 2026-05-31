import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface AuthState {
  token: string | null;
  tenantId: string | null;
  username: string | null;
  roles: string[];
  isAuthenticated: boolean;
}

const initialState: AuthState = {
  token: null,
  tenantId: null,
  username: null,
  roles: [],
  isAuthenticated: false,
};

export const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{ token: string; tenantId: string; username: string; roles: string[] }>
    ) => {
      state.token = action.payload.token;
      state.tenantId = action.payload.tenantId;
      state.username = action.payload.username;
      state.roles = action.payload.roles;
      state.isAuthenticated = true;
    },
    logout: (state) => {
      state.token = null;
      state.tenantId = null;
      state.username = null;
      state.roles = [];
      state.isAuthenticated = false;
    },
  },
});

export const { setCredentials, logout } = authSlice.actions;
export default authSlice.reducer;
