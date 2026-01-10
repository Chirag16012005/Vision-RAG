import { configureStore } from '@reduxjs/toolkit';
import { generalReducer } from './generalSlicer';

const store = configureStore({
    reducer: {
        general: generalReducer,
    },
});

export default store;
