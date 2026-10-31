# Saldo inicial, profit, saldo final y numeros rojos

Periodo: 26 al 30 de octubre de 2026.

**Banco.** Antes del 26 ya tenia un ingreso de apertura de 1,000.00 (del 25), asi que su **saldo inicial** es
1,000.00. Ese ingreso no se vuelve a sumar en los ingresos del periodo. En el periodo entraron 3,000.00 y
salieron 1,200.00 + 1,000.00 = 2,200.00, entonces su **profit** es 3,000.00 - 2,200.00 = **800.00**. El
**saldo final** es el inicial mas el profit: 1,000.00 + 800.00 = **1,800.00**. El profit y el saldo final son
distintos porque Banco ya tenia dinero al empezar. Si solo se ve el 28, el profit del dia es -1,000.00, pero el
saldo final sigue en 1,800.00: un dia negativo no deja la cuenta en rojo.

**Caja.** No tenia nada antes del 26 (saldo inicial 0.00). Entraron 500.00 y salieron 700.00, asi que su profit
es **-200.00** y, como empezo en cero, su saldo final tambien es **-200.00**. Esta en **numeros rojos** porque su
saldo final es menor que cero. Tener cero no seria estar en rojo.

**General.** Sumando las tres cuentas: inicial 1,000.00, ingresos 3,500.00, egresos 2,900.00, profit 600.00 y
saldo final 1,600.00. El total es positivo (`isInRed: false`) pero Caja sigue en rojo (`accountsInRed: 1`). Por
eso se devuelven los dos datos: el total positivo esconde que una cuenta esta en negativo.
