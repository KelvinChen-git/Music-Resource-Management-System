/**
 * 密码强度验证工具
 * 
 * 强密码需满足条件：
 * 1. 至少8个字符长度
 * 2. 至少包含一个大写字母
 * 3. 至少包含一个小写字母
 * 4. 至少包含一个数字
 * 5. 至少包含一个特殊字符 (!@#$%^&*(),.?":{}|<>)
 */

/**
 * 验证密码是否包含至少一个大写字母
 * @param {string} password 密码字符串
 * @returns {boolean} 是否通过验证
 */
export const hasUpperCase = (password) => {
  return /[A-Z]/.test(password);
};

/**
 * 验证密码是否包含至少一个小写字母
 * @param {string} password 密码字符串
 * @returns {boolean} 是否通过验证
 */
export const hasLowerCase = (password) => {
  return /[a-z]/.test(password);
};

/**
 * 验证密码是否包含至少一个数字
 * @param {string} password 密码字符串
 * @returns {boolean} 是否通过验证
 */
export const hasNumber = (password) => {
  return /[0-9]/.test(password);
};

/**
 * 验证密码是否包含至少一个特殊字符
 * @param {string} password 密码字符串
 * @returns {boolean} 是否通过验证
 */
export const hasSpecialChar = (password) => {
  return /[!@#$%^&*(),.?":{}|<>]/.test(password);
};

/**
 * 验证密码是否达到最小长度要求
 * @param {string} password 密码字符串
 * @param {number} minLength 最小长度
 * @returns {boolean} 是否通过验证
 */
export const hasMinLength = (password, minLength = 8) => {
  return password.length >= minLength;
};

/**
 * 完整的密码强度验证函数
 * @param {string} password 密码字符串
 * @returns {Object} 验证结果，包含是否通过验证和错误信息
 */
export const validatePasswordStrength = (password) => {
  const result = {
    valid: true,
    message: ''
  };

  if (!hasMinLength(password)) {
    result.valid = false;
    result.message = 'Password must be at least 8 characters';
    return result;
  }

  if (!hasUpperCase(password)) {
    result.valid = false;
    result.message = 'Password must contain at least one uppercase letter';
    return result;
  }

  if (!hasLowerCase(password)) {
    result.valid = false;
    result.message = 'Password must contain at least one lowercase letter';
    return result;
  }

  if (!hasNumber(password)) {
    result.valid = false;
    result.message = 'Password must contain at least one number';
    return result;
  }

  if (!hasSpecialChar(password)) {
    result.valid = false;
    result.message = 'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)';
    return result;
  }

  return result;
};

/**
 * Element Plus 表单验证器
 * @param {Object} rule 规则对象
 * @param {string} value 表单值
 * @param {Function} callback 回调函数
 */
export const validatePassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Please enter your password'));
    return;
  }
  
  const result = validatePasswordStrength(value);
  if (!result.valid) {
    callback(new Error(result.message));
    return;
  }
  
  callback();
};

export default {
  validatePassword,
  validatePasswordStrength,
  hasUpperCase,
  hasLowerCase,
  hasNumber,
  hasSpecialChar,
  hasMinLength
}; 