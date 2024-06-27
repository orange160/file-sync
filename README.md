## 文件同步
> 一个PyQt6项目，用于SFTP升级服务器程序。
>
> 支持多服务器同步，可自由切换
> 
>  Python版本: 3.11.5

### 功能

- 如果本地文件MD5值和服务器文件MD5值不一致，上传文件
- 如果本地服务器有文件，服务器上没有，上传文件
- 如果服务器上有数据，本地没有，删除服务器文件

### 打包

> 使用pyinstaller打包成一个exe文件

```
pyinstaller -F -w ^
 -i resources/images/logo.ico ^
 --add-data "resources:resources" ^
 --additional-hooks-dir=hooks ^
 -n FileSync ^
 main.py
  
# 参数说明:
#   ^ 是windows中命令的换行符，^符号后不要有空格
#   -F 打包成一个exe文件
#   -w 运行exe文件时禁止弹出CMD窗口
#   -i 指定exe文件的图标
#   --additional-hooks-dir=hooks  指定自定义的hook路径
#   --add-data 将代码中images文件夹中所有的文件打包进exe的images文件夹中，格式为 resource:destination
#   -n 指定输出的exe文件的文件名称
```

