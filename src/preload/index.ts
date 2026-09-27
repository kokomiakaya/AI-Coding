import { contextBridge } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

// 业务接口：M3 阶段会在这里加上账单的增删改查接口
const api = {}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.electron = electronAPI
  // @ts-ignore (define in dts)
  window.api = api
}
