import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import qs from 'qs' // 导入 qs

// 创建axios实例
const service = axios.create({
  baseURL: '/api', // 根据后端配置的context-path
  timeout: 10000, // 请求超时时间
  // 添加 paramsSerializer
  paramsSerializer: params => {
    // 使用 qs 序列化参数
    // arrayFormat: 'repeat' 会将数组序列化为 key=value1&key=value2
    return qs.stringify(params, { arrayFormat: 'repeat' })
  }
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 先检查localStorage，再检查sessionStorage
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    // 检查是否是blob类型的响应（文件下载）
    if (response.config.responseType === 'blob') {
      // 为了防止开发工具尝试读取blob的responseText导致错误
      // 我们在这里直接返回响应数据，不做额外处理
      // 如果是错误响应转换成blob的情况，可以通过检查响应头或blob类型进行区分
      const contentType = response.headers['content-type'];
      if (contentType && contentType.includes('application/json')) {
        // 这可能是一个错误响应被转为blob
        // 但我们在此处仍然返回blob，让具体处理函数去解析
        console.log('返回的是JSON格式的blob数据');
      }
      return response.data;
    }
    
    const res = response.data
    
    // 如果返回的状态码不是200，说明接口出错
    if (res.code !== 200) {
      ElMessage.error(res.message || '系统错误')
      return Promise.reject(new Error(res.message || '系统错误'))
    }
    
    return res
  },
  error => {
    // 构建更详细的错误信息
    let errorMsg = '请求失败';
    
    if (error.response) {
      // 服务器返回了错误状态码
      const status = error.response.status;
      switch(status) {
        case 400:
          errorMsg = '请求参数错误';
          break;
        case 401:
          errorMsg = '未授权，请重新登录';
          // token过期或未登录，清除所有存储的token
          localStorage.removeItem('token');
          sessionStorage.removeItem('token');
          router.push('/login');
          break;
        case 403:
          errorMsg = '拒绝访问';
          break;
        case 404:
          errorMsg = '请求的资源不存在';
          break;
        case 500:
          errorMsg = '服务器内部错误';
          break;
        default:
          errorMsg = `请求错误 (${status})`;
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      if (error.message.includes('timeout')) {
        errorMsg = '请求超时!';
      } else {
        errorMsg = '网络错误，请检查您的网络连接';
      }
    } else {
      // 发送请求时出现错误
      errorMsg = error.message;
    }
    
    // 如果响应类型是blob，直接返回一个标记了错误的blob
    if (error.config && error.config.responseType === 'blob') {
      // 创建一个包含错误信息的Blob
      const errorBlob = new Blob([JSON.stringify({
        success: false,
        message: errorMsg,
        errorCode: error.response?.status || 'UNKNOWN'
      })], { type: 'application/json' });
      
      // 在blob上添加错误标记
      errorBlob.isError = true;
      errorBlob.errorMessage = errorMsg;
      
      return Promise.reject(new Error(errorMsg));
    }
    
    ElMessage.error(errorMsg)
    return Promise.reject(error)
  }
)

export default service 