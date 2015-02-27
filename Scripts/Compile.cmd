mxmlc -omit-trace-statements=false -static-link-runtime-shared-libraries=true -compiler.source-path=. Util.as
abcexport Util.swf
rmdir /s /q Util-0
rabcdasm.exe Util-0.abc
pause
