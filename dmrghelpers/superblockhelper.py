"""
简化有关superblock的调用
"""

import numpy
import scipy.sparse
from fermionic.block import LeftBlockExtend, RightBlockExtend
from fermionic.superblock import SuperBlockExtend
from fermionic.baseop import Hamiltonian, BaseOperator

def extend_merge_to_superblock(
        lbkext: LeftBlockExtend,
        rbkext: RightBlockExtend
    ):
    '''将两个extend合并成superblock'''
    return SuperBlockExtend(lbkext, rbkext)


def leftext_hamiltonian_to_superblock(
        sbext: SuperBlockExtend,
        ham: Hamiltonian
    ):
    '''将leftblockextend基上的hamiltonian扩展到superblock基上'''
    #原本的哈密顿量在|phi^n-1, s^n>上
    #现在要弄到 |phi^n-1, s^n, s^n+1, phi^N-(n+1)>上
    # H' = H X I
    #右边的是高位
    highbit = sbext.rightblockextend.dim
    lowbitlen = sbext.leftblockextend.dim
    if lowbitlen != ham.basis.dim:
        raise ValueError('算符的基不一致')
    #
    mat = scipy.sparse.block_diag([ham.mat] * highbit)
    return Hamiltonian(sbext, mat)


def leftext_oper_to_superblock(
        sbext: SuperBlockExtend,
        oper: BaseOperator
    ):
    '''将leftblockextend上面的算符扩展到superblockextend'''
    #原本的算符在|phi^n-1, s^n>上面
    #现在增加到|phi^n-1, s^n, s^n+1, phi^N-(n+1)>
    #没有影响正常的算符顺序，不会有反对易的符号所以扩展的方式和哈密顿量是差不多的
    #
    highbit = sbext.rightblockextend.dim
    lowbitlen = sbext.leftblockextend.dim
    if lowbitlen != oper.basis.dim:
        raise ValueError('算符的基不一致')
    #
    mat = scipy.sparse.block_diag([oper.mat] * highbit)
    return BaseOperator(oper.siteidx, sbext, oper.isferm, mat, spin=oper.spin)


def rightext_hamiltonian_to_superblock(
        sbext: SuperBlockExtend,
        ham: Hamiltonian
    ):
    '''把rightblockextend基上面的哈密顿量扩展到superblock上\n
    Issue#2: 优化算法以提升速度
    '''
    #原本的哈密顿量在|s^n+1, phi^N-(n+1)>上
    #现在要弄到 |phi^n-1, s^n, s^n+1, phi^N-(n+1)>上
    # H' = I X H，由于哈密顿量里面都是算符的二次项，而且right中的
    #编号都比左边要大，所以不会产生反对易的符号
    eyedim = sbext.leftblockextend.dim
    hammat = ham.mat.todok()\
        if scipy.sparse.isspmatrix_coo(ham.mat) else ham.mat
    #
    speye = scipy.sparse.eye(eyedim).tocsr()
    #
    block_arr = numpy.array([[None]*sbext.rightblockextend.dim]\
        *sbext.rightblockextend.dim)
    idxllist, idxrlist = hammat.nonzero()
    for lidx, ridx in zip(idxllist, idxrlist):
        block_arr[lidx, ridx] = speye.multiply(hammat[lidx, ridx])
    for idx in range(sbext.rightblockextend.dim):
        if block_arr[idx, idx] is None:
            block_arr[idx, idx] = scipy.sparse.dok_matrix((eyedim, eyedim))
    mat = scipy.sparse.bmat(block_arr)
    return Hamiltonian(sbext, mat)


def rightext_oper_to_superblock(
        sbext: SuperBlockExtend,
        oper: BaseOperator
    ):
    '''把rightblockextend基上面的算符扩展到superblock上\n
    Issue#2: 优化算法以提升速度
    '''
    #原本的算符在|s^n+1, phi^N-(n+1)>上
    #现在要弄到 |phi^n-1, s^n, s^n+1, phi^N-(n+1)>上
    # O' = I X O，这时的算符会经过phi^n-1和s^n中所有的产生算符
    #才能到|s^n+1, phi^N-(n+1)>上
    eyedim = sbext.leftblockextend.dim
    opermat = oper.mat.todok()\
        if scipy.sparse.isspmatrix_coo(oper.mat) else oper.mat
    speye = None
    if oper.isferm:
        eyevals = []
        for idx in sbext.leftblockextend.iter_idx():
            _pnum = sbext.leftblockextend.spin_nums[idx]
            _partinum = numpy.sum(_pnum)
            eyevals.append(1. if _partinum % 2 == 0 else -1.)
            speye = scipy.sparse.dia_matrix((eyevals, 0), shape=(eyedim, eyedim))
    else:
        speye = scipy.sparse.eye(eyedim)
    speye = speye.tocsr()
    #
    block_arr = numpy.array([[None]*sbext.rightblockextend.dim]\
        *sbext.rightblockextend.dim)
    idxllist, idxrlist = opermat.nonzero()
    for lidx, ridx in zip(idxllist, idxrlist):
        block_arr[lidx, ridx] = speye.multiply(opermat[lidx, ridx])
    for idx in range(sbext.rightblockextend.dim):
        if block_arr[idx, idx] is None:
            block_arr[idx, idx] = scipy.sparse.dok_matrix((eyedim, eyedim))
    mat = scipy.sparse.bmat(block_arr)
    return BaseOperator(oper.siteidx, sbext, oper.isferm, mat, spin=oper.spin)
