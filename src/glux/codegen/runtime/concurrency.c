/*
 * Glux併發運行時支持
 * 提供併發任務管理、Future處理等功能
 */

#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <string.h>
#include <unistd.h>

/* Future結構體定義 */
typedef struct {
    void* result;           // 結果指針
    int status;             // 狀態: 0=未完成, 1=已完成, 2=錯誤
    int is_multi_value;     // 是否為多值Future
    int result_type_id;     // 結果類型ID
    int task_id;            // 任務ID
    char* error_message;    // 錯誤消息
    pthread_mutex_t mutex;  // 互斥鎖,用於保護Future狀態
    pthread_cond_t cond;    // 條件變量,用於等待任務完成
} Future;

/* 任務參數封裝結構體 */
typedef struct {
    void* (*task_func)(void*);  // 任務函數
    void* arg;                  // 任務參數
    Future* future;             // 對應的Future
} TaskWrapper;

/* 全局任務計數器 */
static int task_counter = 0;
static pthread_mutex_t task_counter_mutex = PTHREAD_MUTEX_INITIALIZER;

/* 獲取新的任務ID */
static int get_next_task_id() {
    int id;
    pthread_mutex_lock(&task_counter_mutex);
    id = task_counter++;
    pthread_mutex_unlock(&task_counter_mutex);
    return id;
}

/* 任務線程函數 */
static void* task_thread(void* arg) {
    TaskWrapper* wrapper = (TaskWrapper*)arg;
    void* result = NULL;
    
    // 執行任務函數
    result = wrapper->task_func(wrapper->arg);
    
    // 設置Future結果
    pthread_mutex_lock(&wrapper->future->mutex);
    wrapper->future->result = result;
    wrapper->future->status = 1;  // 設置為已完成
    pthread_cond_broadcast(&wrapper->future->cond);  // 通知所有等待者
    pthread_mutex_unlock(&wrapper->future->mutex);
    
    // 釋放包裝器
    free(wrapper);
    
    return NULL;
}

/* 創建新的Future */
Future* __glux_create_future(int type_id) {
    Future* future = (Future*)malloc(sizeof(Future));
    if (!future) {
        fprintf(stderr, "錯誤: 無法分配Future內存\n");
        exit(1);
    }
    
    future->result = NULL;
    future->status = 0;  // 未完成
    future->is_multi_value = 0;
    future->result_type_id = type_id;
    future->task_id = -1;  // 暫未分配
    future->error_message = NULL;
    
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    
    return future;
}

/* 啟動任務 */
int __glux_spawn_task(void* (*task_func)(void*), void* arg, Future* future) {
    pthread_t thread;
    TaskWrapper* wrapper;
    
    // 分配任務包裝器
    wrapper = (TaskWrapper*)malloc(sizeof(TaskWrapper));
    if (!wrapper) {
        fprintf(stderr, "錯誤: 無法分配任務包裝器內存\n");
        exit(1);
    }
    
    // 初始化包裝器
    wrapper->task_func = task_func;
    wrapper->arg = arg;
    wrapper->future = future;
    
    // 設置任務ID
    future->task_id = get_next_task_id();
    
    // 創建線程
    if (pthread_create(&thread, NULL, task_thread, wrapper) != 0) {
        fprintf(stderr, "錯誤: 無法創建線程\n");
        free(wrapper);
        future->status = 2;  // 設置為錯誤狀態
        future->error_message = strdup("線程創建失敗");
        return -1;
    }
    
    // 分離線程
    pthread_detach(thread);
    
    return future->task_id;
}

/* 等待單個Future完成 */
void* __glux_await_future(Future* future) {
    void* result;
    
    if (!future) {
        fprintf(stderr, "錯誤: 嘗試等待空Future\n");
        return NULL;
    }
    
    // 等待Future完成
    pthread_mutex_lock(&future->mutex);
    while (future->status == 0) {
        pthread_cond_wait(&future->cond, &future->mutex);
    }
    
    result = future->result;
    pthread_mutex_unlock(&future->mutex);
    
    // 檢查是否有錯誤
    if (future->status == 2) {
        fprintf(stderr, "錯誤: 任務執行失敗: %s\n",
                future->error_message ? future->error_message : "未知錯誤");
        return NULL;
    }
    
    return result;
}

/* 創建多值結果數組 */
void** __create_multi_result(Future** futures, int count) {
    void** results = (void**)malloc(sizeof(void*) * count);
    if (!results) {
        fprintf(stderr, "錯誤: 無法分配多值結果數組內存\n");
        exit(1);
    }
    
    for (int i = 0; i < count; i++) {
        results[i] = futures[i]->result;
    }
    
    return results;
}

/* 等待多個Future完成 */
void* __glux_await_multiple(Future** futures, int count) {
    if (!futures || count <= 0) {
        fprintf(stderr, "錯誤: 無效的多Future等待\n");
        return NULL;
    }
    
    // 等待所有Future完成
    for (int i = 0; i < count; i++) {
        if (!futures[i]) continue;
        
        pthread_mutex_lock(&futures[i]->mutex);
        while (futures[i]->status == 0) {
            pthread_cond_wait(&futures[i]->cond, &futures[i]->mutex);
        }
        pthread_mutex_unlock(&futures[i]->mutex);
        
        // 檢查是否有錯誤
        if (futures[i]->status == 2) {
            fprintf(stderr, "錯誤: 任務 %d 執行失敗: %s\n",
                    futures[i]->task_id,
                    futures[i]->error_message ? futures[i]->error_message : "未知錯誤");
            // 繼續等待其他任務
        }
    }
    
    // 創建結果數組
    return __create_multi_result(futures, count);
}

/* 釋放Future資源 */
void __glux_free_future(Future* future) {
    if (!future) return;
    
    pthread_mutex_destroy(&future->mutex);
    pthread_cond_destroy(&future->cond);
    
    if (future->error_message) {
        free(future->error_message);
    }
    
    free(future);
}

/* 獲取多值結果中的元素 */
void* __glux_get_multi_result(void** results, int index) {
    if (!results) return NULL;
    return results[index];
}

/* 釋放多值結果 */
void __glux_free_multi_result(void** results) {
    if (results) {
        free(results);
    }
} 