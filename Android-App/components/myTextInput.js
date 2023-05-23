import React, { useState } from 'react';
import { TextInput, StyleSheet, Alert } from 'react-native';

const MyTextInput = ({defaultValue,placeholder,updateParent}) => {
  const [isFocused, setIsFocused] = useState(false);
  const [inputValue, setInputValue] = useState(defaultValue);
  
  return (
    <TextInput
      style={[
        styles.input,
        isFocused ? styles.focused : null,
      ]}
      defaultValue = {defaultValue}
      placeholder = {placeholder}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      onChangeText={(inputValue) => {setInputValue(inputValue);updateParent(inputValue);}}
      //setInputValue是异步函数，把inputValue作为参数传递给onChangText是为了及时更新
    />
  );
};

const styles = StyleSheet.create({
  input: {
    height: 50,
    margin: 20,
    marginTop: 15,
    marginBottom: 35,
    padding:10,
    fontSize: 20,
    borderWidth: 1,
    borderRadius: 10,
    borderColor: 'black',
  },
  focused: {
    borderColor: 'green',
    borderWidth: 2
  },
});

export default MyTextInput;