# Week 1 Python Programs

The `easy` and `medium` folders contain the practice programs.

## How to run a program

1. Open a PowerShell terminal.
2. Go to the repository:

   ```powershell
   cd "D:\THDC python course\ai-bridge"
   ```

3. Run the Python file:

   ```powershell
   python "week 1/easy/even_or_odd.py"
   ```

4. When `Enter an integer:` appears, type a whole number and press **Enter**.
5. Read the result. Run the command again to test another number.

Keep the quotes around the file path because `week 1` contains a space.

## Test Even or Odd

| Input | Expected output |
| --- | --- |
| `4` | `Even` |
| `7` | `Odd` |
| `0` | `Even` |
| `-6` | `Even` |
| `-3` | `Odd` |

The current program accepts whole numbers. Text such as `hello` or decimals such as `2.5` cause a `ValueError`.

## Run other programs

Replace the folder and filename in the command with the program you want to run. For example:

```powershell
python "week 1/easy/fizzbuzz.py"
python "week 1/medium/binary_search.py"
```

Files containing only a task comment will finish without displaying anything until you add code.

## If Python is not recognized

Try the Windows Python launcher:

```powershell
py "week 1/easy/even_or_odd.py"
```

If neither `python` nor `py` works, install Python and reopen your terminal.
